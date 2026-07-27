"""Shared in-process state for the currently cloned/indexed repository, plus the
helper functions that mutate it. The app is still single-repo-at-a-time — every
router reads/writes these module-level globals rather than each other's state,
which is why this lives in one place instead of being duplicated per router.
"""
import os
import stat
import threading
from datetime import datetime, timezone

from fastapi import HTTPException
from git import Repo

from app.config import REPO_PATH, BINARY_SKIP_EXTENSIONS, MAX_INDEXABLE_FILE_SIZE
from app.storage.db import get_session
from app.storage.models import Repository, Branch, File as FileRow, Report
from app.storage.vectordb import store_embeddings
from app import parsers
from app.parsers.base import empty_analysis
from app.analysis.scanner import scan_repository
from app.analysis.indexer import build_index
from app.analysis.chunker import chunk_repository
from app.storage.embeddings import embed_chunks
from app.analysis.callgraph import build_call_graph

LANGUAGE_PARSERS = parsers.build_registry()
TEXT_EXTENSIONS = {
    ".md", ".txt", ".rst", ".json", ".yaml", ".yml", ".toml", ".cfg", ".ini",
    ".env.example", ".xml", ".html", ".css",
}

REPOSITORY_DATA = []
EMBEDDED_CHUNKS = []
INDEX = None
ISSUES_REPORT = None
DEPENDENCY_REPORT = None
ARCHITECTURE_REPORT = None
CALL_GRAPH_REPORT = None
DEAD_CODE_REPORT = None
HOTSPOTS_REPORT = None

# Persisted counterparts of the state above (Postgres row ids for the repo/branch
# currently checked out on disk). The app is still single-repo-at-a-time until
# full multi-tenant branch tracking lands — this just stops that state from
# being wiped on restart.
CURRENT_REPOSITORY_ID = None
CURRENT_BRANCH_ID = None


def get_file_analysis(full_path, relative_path):
    """Reuse the parse already done during /build (REPOSITORY_DATA) instead of
    re-opening and re-parsing the file from disk — used by /file-info and
    /dependencies. Falls back to a fresh parse if the file isn't in the
    current index (e.g. skipped as binary/oversized, or no build has run yet)."""
    for entry in REPOSITORY_DATA:
        if entry["path"] == relative_path:
            return entry["analysis"]

    parser_module = LANGUAGE_PARSERS.get(os.path.splitext(full_path)[1].lower())
    if parser_module is None:
        return None
    try:
        return parser_module.analyze_file(full_path)
    except OSError:
        return None


def rehydrate_from_db():
    """Warm the in-process caches above from Postgres on startup. REPOSITORY_DATA,
    INDEX and the *_REPORT globals are all reconstructible from data Postgres
    already durably holds (files.analysis, reports.*) — without this, a process
    restart would silently forget the most recently built repo/branch and force
    a full rebuild even though nothing was actually lost."""
    global CURRENT_REPOSITORY_ID, CURRENT_BRANCH_ID, REPOSITORY_DATA, INDEX
    global ISSUES_REPORT, DEPENDENCY_REPORT, ARCHITECTURE_REPORT, CALL_GRAPH_REPORT
    global DEAD_CODE_REPORT, HOTSPOTS_REPORT

    session = get_session()
    try:
        repository = (
            session.query(Repository)
            .filter(Repository.status == "built")
            .order_by(Repository.built_at.desc())
            .first()
        )
        if repository is None:
            return

        branch = (
            session.query(Branch)
            .filter(Branch.repository_id == repository.id, Branch.indexed_at.isnot(None))
            .order_by(Branch.indexed_at.desc())
            .first()
        )
        if branch is None:
            return

        CURRENT_REPOSITORY_ID = repository.id
        CURRENT_BRANCH_ID = branch.id

        files = session.query(FileRow).filter(FileRow.branch_id == branch.id).all()
        REPOSITORY_DATA = [{"path": f.path, "analysis": f.analysis} for f in files]
        if REPOSITORY_DATA:
            INDEX = build_index(REPOSITORY_DATA)

        report = session.get(Report, branch.id)
        if report is not None:
            ISSUES_REPORT = report.issues_report
            DEPENDENCY_REPORT = report.dependency_report
            ARCHITECTURE_REPORT = report.architecture_report
            CALL_GRAPH_REPORT = report.call_graph_report
            DEAD_CODE_REPORT = report.dead_code_report
            HOTSPOTS_REPORT = report.hotspots_report
    finally:
        session.close()


def reset_report_caches():
    """Invalidate every cached, expensive-to-recompute report — called whenever
    the checked-out code actually changes (build, branch switch, webhook push),
    so a stale architecture/call-graph/dead-code/hotspots report never survives
    past the commit it was computed for."""
    global ISSUES_REPORT, DEPENDENCY_REPORT, ARCHITECTURE_REPORT, CALL_GRAPH_REPORT
    global DEAD_CODE_REPORT, HOTSPOTS_REPORT
    ISSUES_REPORT = None
    DEPENDENCY_REPORT = None
    ARCHITECTURE_REPORT = None
    CALL_GRAPH_REPORT = None
    DEAD_CODE_REPORT = None
    HOTSPOTS_REPORT = None


def clear_readonly_and_retry(func, path, exc):
    """shutil.rmtree onexc handler: git marks pack/idx files read-only,
    which makes Windows raise WinError 5 on delete. Clear the flag and retry."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def analyze_repository(repo_path, branch_id):

    repository_data = []
    files = scan_repository(repo_path)

    for file in files:
        ext = file["extension"].lower()

        if ext in BINARY_SKIP_EXTENSIONS or file["size"] > MAX_INDEXABLE_FILE_SIZE:
            continue

        parser_module = LANGUAGE_PARSERS.get(ext)

        if parser_module is not None:
            try:
                result = parser_module.analyze_file(file["full_path"])
            except Exception:
                continue

        elif ext in TEXT_EXTENSIONS or ext == "":
            try:
                with open(file["full_path"], "rb") as f:
                    raw_bytes = f.read()
            except OSError:
                continue
            if b"\x00" in raw_bytes:
                # Binary content masquerading as text (e.g. a model weight
                # shard with no extension) — not indexable, and a literal NUL
                # byte would fail the Postgres JSONB insert in persist_files.
                continue
            result = empty_analysis()
            result["raw_text"] = raw_bytes.decode("utf-8", errors="ignore")

        else:
            continue

        repository_data.append({
            "path": file["path"],
            "analysis": result,
        })

    global REPOSITORY_DATA
    REPOSITORY_DATA = repository_data

    index = build_index(repository_data)

    chunks = chunk_repository(repository_data)

    global EMBEDDED_CHUNKS
    EMBEDDED_CHUNKS = embed_chunks(chunks)

    store_embeddings(EMBEDDED_CHUNKS, branch_id=branch_id)

    print("Chunks:", len(EMBEDDED_CHUNKS))

    persist_files(branch_id, repository_data)

    return index


def _strip_nul_bytes(value):
    """Postgres's JSONB/text columns can never store a literal NUL byte — this
    is a hard Postgres limitation, not an encoding setting. analyze_repository
    already skips whole-file binary content, but this is a second, cheap
    safety net in case a NUL sneaks in some other way (e.g. a source file a
    language parser reads that happens to contain one)."""
    if isinstance(value, str):
        return value.replace("\x00", "")
    if isinstance(value, dict):
        return {k: _strip_nul_bytes(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_strip_nul_bytes(v) for v in value]
    return value


def persist_files(branch_id, repository_data):
    """Upsert this build's files into Postgres, replacing whatever the branch had before."""
    session = get_session()
    try:
        session.query(FileRow).filter(FileRow.branch_id == branch_id).delete()
        session.bulk_save_objects([
            FileRow(
                branch_id=branch_id,
                path=item["path"],
                extension=os.path.splitext(item["path"])[1],
                analysis=_strip_nul_bytes(item["analysis"]),
            )
            for item in repository_data
        ])
        session.commit()
    finally:
        session.close()


def list_git_branches(repo_path):
    """Local + remote branch names, e.g. what `git branch -a` would show, de-duped."""
    repo = Repo(repo_path)
    names = {head.name for head in repo.heads}
    try:
        for ref in repo.remotes.origin.refs:
            if ref.name == "origin/HEAD":
                continue
            names.add(ref.name.split("/", 1)[1])
    except (AttributeError, ValueError):
        pass  # no origin remote (shouldn't happen for a freshly cloned repo)
    return sorted(names)


def checkout_branch(repo_path, branch_name):
    repo = Repo(repo_path)
    if branch_name in [head.name for head in repo.heads]:
        repo.git.checkout(branch_name)
    else:
        repo.git.checkout("-b", branch_name, f"origin/{branch_name}")


def get_or_create_branch_id(repository_id, name):
    session = get_session()
    try:
        branch = session.query(Branch).filter_by(repository_id=repository_id, name=name).first()
        if branch is None:
            branch = Branch(repository_id=repository_id, name=name)
            session.add(branch)
            session.commit()
        return branch.id
    finally:
        session.close()


def resolve_branch_id(name):
    """Resolve a branch name to its Qdrant/Postgres branch_id without touching the disk
    checkout — used by search endpoints, which read already-indexed vectors for any branch."""
    if not name:
        return CURRENT_BRANCH_ID
    if CURRENT_REPOSITORY_ID is None:
        raise HTTPException(status_code=400, detail="No repository cloned yet. Call /clone first.")
    return get_or_create_branch_id(CURRENT_REPOSITORY_ID, name)


def reindex_current_branch(name):
    """Resolve/create the branch row, reindex whatever is currently checked out on
    disk under it, and persist indexed_at/last_commit_sha/status. Shared by
    switch_to_branch (manual switch) and handle_github_push (webhook-triggered)."""
    global CURRENT_BRANCH_ID, INDEX

    CURRENT_BRANCH_ID = get_or_create_branch_id(CURRENT_REPOSITORY_ID, name)
    reset_report_caches()
    INDEX = analyze_repository(REPO_PATH, CURRENT_BRANCH_ID)

    session = get_session()
    try:
        branch = session.get(Branch, CURRENT_BRANCH_ID)
        branch.indexed_at = datetime.now(timezone.utc)
        try:
            branch.last_commit_sha = Repo(REPO_PATH).head.commit.hexsha
        except Exception:
            pass

        repository = session.get(Repository, CURRENT_REPOSITORY_ID)
        repository.status = "built"
        repository.built_at = datetime.now(timezone.utc)
        session.commit()
    finally:
        session.close()

    return CURRENT_BRANCH_ID


def switch_to_branch(name):
    """Check out `name` on disk (if needed) and reindex it, making it the active branch."""
    if CURRENT_REPOSITORY_ID is None:
        raise HTTPException(status_code=400, detail="No repository cloned yet. Call /clone first.")

    try:
        checkout_branch(REPO_PATH, name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not check out branch '{name}': {e}")

    branch_id = get_or_create_branch_id(CURRENT_REPOSITORY_ID, name)
    if branch_id == CURRENT_BRANCH_ID:
        return branch_id

    return reindex_current_branch(name)


webhook_lock = threading.Lock()


def handle_github_push(branch_name):
    """Fetch the latest commit for `branch_name` and reindex it. Unlike
    switch_to_branch (fine reusing whatever's already checked out locally), a
    push webhook always implies there's new upstream content, so this fetches
    and hard-resets to origin's tip first."""
    repo = Repo(REPO_PATH)
    repo.remotes.origin.fetch()

    if branch_name in [head.name for head in repo.heads]:
        repo.git.checkout(branch_name)
    else:
        repo.git.checkout("-b", branch_name, f"origin/{branch_name}")
    repo.git.reset("--hard", f"origin/{branch_name}")

    return reindex_current_branch(branch_name)


def upsert_report(**fields):
    if CURRENT_BRANCH_ID is None:
        return
    session = get_session()
    try:
        report = session.get(Report, CURRENT_BRANCH_ID)
        if report is None:
            report = Report(branch_id=CURRENT_BRANCH_ID)
            session.add(report)
        for key, value in fields.items():
            setattr(report, key, value)
        report.updated_at = datetime.now(timezone.utc)
        session.commit()
    finally:
        session.close()


def require_index():
    if INDEX is None:
        raise HTTPException(status_code=400, detail="Repository index not built yet. Call /build first.")


def get_call_graph():
    """Cached build_call_graph() result for the current branch — shared by
    /call-graph, /dead-code, and /ask's RAG context so all three reuse the same
    parse instead of each re-walking every file's AST independently."""
    global CALL_GRAPH_REPORT
    if CALL_GRAPH_REPORT is None:
        files = scan_repository(REPO_PATH)
        CALL_GRAPH_REPORT = build_call_graph(files)
        upsert_report(call_graph_report=CALL_GRAPH_REPORT)
    return CALL_GRAPH_REPORT
