import os
import shutil
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from git import Repo

from app import state
from app.schemas import CloneRequest, SwitchBranchRequest
from app.storage.db import get_session
from app.storage.models import Repository, Branch
from app.analysis.scanner import scan_repository

router = APIRouter()


@router.get("/")
def home():
    return {"message": "Backend Running"}


@router.get("/status")
def status():
    """Lightweight check the frontend can call once on load to decide whether
    to show the home/import screen or jump straight to the dashboard — e.g.
    after a page refresh, or a process restart that rehydrated from Postgres."""
    return {
        "repo_loaded": state.CURRENT_REPOSITORY_ID is not None and state.INDEX is not None,
        "repository_id": state.CURRENT_REPOSITORY_ID,
        "branch_id": state.CURRENT_BRANCH_ID,
    }


@router.post("/clone")
async def clone_repository(payload: CloneRequest):
    repo_url = payload.url.strip()
    if not repo_url:
        raise HTTPException(status_code=400, detail="Repository URL cannot be empty.")

    # A fresh clone invalidates everything derived from the previous one.
    state.REPOSITORY_DATA = []
    state.EMBEDDED_CHUNKS_COUNT = 0
    state.EMBEDDING_DIMENSION = 0
    state.INDEX = None
    state.reset_report_caches()
    state.CURRENT_REPOSITORY_ID = None
    state.CURRENT_BRANCH_ID = None

    if os.path.exists(state.REPO_PATH):
        try:
            shutil.rmtree(state.REPO_PATH, onexc=state.clear_readonly_and_retry)
        except Exception as e:
            print(f"Warning clearing repo dir: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Could not clear previous repository before cloning: {e}",
            )

    os.makedirs(os.path.dirname(state.REPO_PATH), exist_ok=True)

    session = get_session()
    try:
        repository = Repository(url=repo_url, status="cloning")
        session.add(repository)
        session.commit()

        try:
            # No depth limit: branch tracking needs every branch's ref, and git
            # history intelligence needs full commit history, not just the tip.
            Repo.clone_from(repo_url, state.REPO_PATH)
        except Exception as e:
            repository.status = "failed"
            repository.error_message = str(e)
            session.commit()
            print(f"Git Clone Error: {e}")
            raise HTTPException(status_code=400, detail=f"Git failed to clone. Check if repository is public: {e}")

        try:
            branch_name = Repo(state.REPO_PATH).active_branch.name
        except Exception:
            branch_name = "main"  # detached HEAD or similar edge case

        branch = Branch(repository_id=repository.id, name=branch_name, is_default=True)
        session.add(branch)
        repository.status = "cloned"
        repository.cloned_at = datetime.now(timezone.utc)
        session.commit()

        state.CURRENT_REPOSITORY_ID = repository.id
        state.CURRENT_BRANCH_ID = branch.id

        return {"status": "success", "message": f"Successfully cloned {repo_url}"}
    finally:
        session.close()


@router.get("/scan")
def scan():
    files = scan_repository(state.REPO_PATH)
    return {
        "total_files": len(files),
        "files": files,
    }


@router.get("/analyze")
def analyze():
    return {
        "chunks_created": state.EMBEDDED_CHUNKS_COUNT,
        "embedding_dimension": state.EMBEDDING_DIMENSION,
    }


@router.post("/build")
def build_repository():
    if state.CURRENT_REPOSITORY_ID is None or state.CURRENT_BRANCH_ID is None:
        raise HTTPException(status_code=400, detail="No repository cloned yet. Call /clone first.")

    state.reset_report_caches()
    state.INDEX = state.analyze_repository(state.REPO_PATH, state.CURRENT_BRANCH_ID)

    session = get_session()
    try:
        branch = session.get(Branch, state.CURRENT_BRANCH_ID)
        branch.indexed_at = datetime.now(timezone.utc)
        try:
            branch.last_commit_sha = Repo(state.REPO_PATH).head.commit.hexsha
        except Exception:
            pass

        repository = session.get(Repository, state.CURRENT_REPOSITORY_ID)
        repository.status = "built"
        repository.built_at = datetime.now(timezone.utc)

        session.commit()
    finally:
        session.close()

    return {
        "message": "Repository indexed successfully",
        "chunks": state.EMBEDDED_CHUNKS_COUNT,
        "files_indexed": len(state.REPOSITORY_DATA),
    }


@router.get("/branches")
def list_branches():
    if state.CURRENT_REPOSITORY_ID is None:
        raise HTTPException(status_code=400, detail="No repository cloned yet. Call /clone first.")

    git_branches = state.list_git_branches(state.REPO_PATH)
    current_name = Repo(state.REPO_PATH).active_branch.name

    session = get_session()
    try:
        indexed = {
            b.name: {"indexed_at": b.indexed_at.isoformat() if b.indexed_at else None,
                      "last_commit_sha": b.last_commit_sha}
            for b in session.query(Branch).filter_by(repository_id=state.CURRENT_REPOSITORY_ID).all()
        }
    finally:
        session.close()

    return {
        "current": current_name,
        "branches": [
            {"name": name, **indexed.get(name, {"indexed_at": None, "last_commit_sha": None})}
            for name in git_branches
        ],
    }


@router.post("/switch-branch")
def switch_branch(request: SwitchBranchRequest):
    state.switch_to_branch(request.name)
    return {
        "message": f"Switched to branch '{request.name}'",
        "branch": request.name,
        "chunks": state.EMBEDDED_CHUNKS_COUNT,
        "files_indexed": len(state.REPOSITORY_DATA),
    }
