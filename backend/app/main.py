import os
import shutil
import stat

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from git import Repo
from dotenv import load_dotenv

load_dotenv()  # Loads variables from .env into os.environ

from app.vectordb import store_embeddings, semantic_search, collection_size
from app.llm import ask_llm
from app.scanner import scan_repository
from app.parser import analyze_file
from app import js_parser
from app.indexer import build_index
from app.search import (
    find_function,
    find_class,
    find_import,
    find_calls,
)
from app.chunker import chunk_repository
from app.embeddings import embed_chunks
from app.retriever import filter_results
from app.summary import summarize_repository
from app.explainer import explain_file
from app.references import find_references
from app.callgraph import build_call_graph, find_function_calls
from app.dependency import get_dependencies
from app.architecture import generate_architecture
from app.file_info import get_file_info
from app.issues import scan_repository as scan_issues
from app.dependency_scan import generate_dependency_report

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REPO_PATH = os.path.join("repos", "repository")

JS_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
TEXT_EXTENSIONS = {
    ".md", ".txt", ".rst", ".json", ".yaml", ".yml", ".toml", ".cfg", ".ini",
    ".env.example", ".xml", ".html", ".css",
}
BINARY_SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp", ".bmp",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".pdf", ".zip", ".gz", ".tar", ".7z",
    ".lock", ".map", ".pyc", ".so", ".dll", ".exe", ".bin",
}
MAX_INDEXABLE_FILE_SIZE = 400_000

REPOSITORY_DATA = []
EMBEDDED_CHUNKS = []
INDEX = None
ISSUES_REPORT = None
DEPENDENCY_REPORT = None


def _clear_readonly_and_retry(func, path, exc):
    """shutil.rmtree onexc handler: git marks pack/idx files read-only,
    which makes Windows raise WinError 5 on delete. Clear the flag and retry."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def _empty_analysis():
    return {"functions": [], "classes": [], "imports": [], "graph": {}}


def analyze_repository(repo_path):

    repository_data = []
    files = scan_repository(repo_path)

    for file in files:
        ext = file["extension"].lower()

        if ext in BINARY_SKIP_EXTENSIONS or file["size"] > MAX_INDEXABLE_FILE_SIZE:
            continue

        if ext == ".py":
            try:
                result = analyze_file(file["full_path"])
            except (SyntaxError, UnicodeDecodeError, OSError):
                continue

        elif ext in JS_EXTENSIONS:
            try:
                result = js_parser.analyze_file(file["full_path"])
            except OSError:
                continue

        elif ext in TEXT_EXTENSIONS or ext == "":
            try:
                with open(file["full_path"], "r", encoding="utf-8", errors="ignore") as f:
                    raw_text = f.read()
            except OSError:
                continue
            result = _empty_analysis()
            result["raw_text"] = raw_text

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

    store_embeddings(EMBEDDED_CHUNKS)

    print("Chunks:", len(EMBEDDED_CHUNKS))

    return index


# ---------------- Request Models ----------------

class CloneRequest(BaseModel):
    url: str


class SearchRequest(BaseModel):
    query: str


class AskRequest(BaseModel):
    question: str


class ExplainRequest(BaseModel):
    path: str


class ReferenceRequest(BaseModel):
    function: str


class CallGraphRequest(BaseModel):
    function: str


class DependencyRequest(BaseModel):
    path: str


class ArchitectureRequest(BaseModel):
    path: str


# ---------------- Routes ----------------

@app.get("/")
def home():
    return {"message": "Backend Running"}


@app.post("/clone")
async def clone_repository(payload: CloneRequest):
    repo_url = payload.url.strip()
    if not repo_url:
        raise HTTPException(status_code=400, detail="Repository URL cannot be empty.")

    # A fresh clone invalidates everything derived from the previous one.
    global REPOSITORY_DATA, EMBEDDED_CHUNKS, INDEX, ISSUES_REPORT, DEPENDENCY_REPORT
    REPOSITORY_DATA = []
    EMBEDDED_CHUNKS = []
    INDEX = None
    ISSUES_REPORT = None
    DEPENDENCY_REPORT = None

    if os.path.exists(REPO_PATH):
        try:
            shutil.rmtree(REPO_PATH, onexc=_clear_readonly_and_retry)
        except Exception as e:
            print(f"Warning clearing repo dir: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Could not clear previous repository before cloning: {e}",
            )

    os.makedirs("repos", exist_ok=True)

    try:
        Repo.clone_from(repo_url, REPO_PATH, depth=1)
        return {"status": "success", "message": f"Successfully cloned {repo_url}"}
    except Exception as e:
        print(f"Git Clone Error: {e}")
        raise HTTPException(status_code=400, detail=f"Git failed to clone. Check if repository is public: {e}")


@app.get("/scan")
def scan():
    files = scan_repository(REPO_PATH)
    return {
        "total_files": len(files),
        "files": files,
    }


@app.get("/analyze")
def analyze():
    return {
        "chunks_created": len(EMBEDDED_CHUNKS),
        "embedding_dimension": len(EMBEDDED_CHUNKS[0]["embedding"]) if EMBEDDED_CHUNKS else 0,
    }


def _require_index():
    if INDEX is None:
        raise HTTPException(status_code=400, detail="Repository index not built yet. Call /build first.")


@app.get("/function/{name}")
def search_function(name: str):
    _require_index()
    return {"path": find_function(INDEX, name)}


@app.get("/class/{name}")
def search_class(name: str):
    _require_index()
    return {"class": name, "path": find_class(INDEX, name)}


@app.get("/import/{name}")
def search_import(name: str):
    _require_index()
    return {"import": name, "path": find_import(INDEX, name)}


@app.get("/calls/{name}")
def search_calls(name: str):
    _require_index()
    return {"function": name, "calls": find_calls(INDEX, name)}


@app.post("/semantic-search")
def semantic_code_search(request: SearchRequest):
    if collection_size() == 0:
        raise HTTPException(status_code=400, detail="No repository indexed yet. Import & build a repository first.")
    return semantic_search(request.query)


@app.post("/ask")
def ask_repository(request: AskRequest):
    if collection_size() == 0:
        raise HTTPException(status_code=400, detail="No repository indexed yet. Import & build a repository first.")

    results = semantic_search(request.question)
    filtered = filter_results(results)

    context = ""
    for chunk in filtered:
        context += chunk["text"] + "\n\n"

    try:
        answer = ask_llm(request.question, context)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM request failed: {e}")

    return {
        "answer": answer,
        "sources": [chunk["metadata"] for chunk in filtered],
    }


@app.get("/summary")
def repository_summary():
    if not REPOSITORY_DATA:
        raise HTTPException(status_code=400, detail="No repository indexed yet. Import & build a repository first.")

    try:
        summary = summarize_repository(REPOSITORY_DATA)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM request failed: {e}")

    return {"summary": summary}


@app.post("/explain-file")
def explain(request: ExplainRequest):
    try:
        explanation = explain_file(request.path)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM request failed: {e}")

    return {
        "path": request.path,
        "explanation": explanation,
    }


@app.post("/references")
def references(request: ReferenceRequest):
    files = scan_repository(REPO_PATH)
    result = find_references(files, request.function)
    return {
        "function": request.function,
        "references": result,
    }


@app.post("/build")
def build_repository():
    global INDEX
    INDEX = analyze_repository(REPO_PATH)

    return {
        "message": "Repository indexed successfully",
        "chunks": len(EMBEDDED_CHUNKS),
        "files_indexed": len(REPOSITORY_DATA),
    }


@app.post("/call-graph")
def call_graph(request: CallGraphRequest):
    files = scan_repository(REPO_PATH)
    graph = build_call_graph(files)
    return {
        "function": request.function,
        "calls": find_function_calls(graph, request.function),
    }


@app.post("/dependencies")
def dependencies(request: DependencyRequest):
    imports = get_dependencies(request.path)
    return {
        "file": request.path,
        "dependencies": imports,
    }


@app.get("/architecture")
def architecture():
    files = scan_repository(REPO_PATH)
    return generate_architecture(files)


@app.post("/architecture")
def architecture_folder(request: ArchitectureRequest):
    files = scan_repository(REPO_PATH)
    return generate_architecture(files, request.path)


@app.get("/file-info")
def file_info(path: str):
    files = scan_repository(REPO_PATH)

    for file in files:
        if file["path"] == path:
            result = get_file_info(file["full_path"], file["path"])

            if result is None:
                raise HTTPException(status_code=400, detail="Unable to parse file.")

            return result

    raise HTTPException(status_code=404, detail="File not found.")


@app.get("/file-content")
def get_file_content(path: str):
    candidates = [path, os.path.join(REPO_PATH, path)]
    resolved = next((c for c in candidates if os.path.exists(c)), None)

    if resolved is None:
        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    try:
        with open(resolved, "r", encoding="utf-8") as f:
            content = f.read()
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/issues")
def get_issues():
    """Repo-wide security & code-quality scan, cached until the next /clone."""
    global ISSUES_REPORT

    if ISSUES_REPORT is None:
        files = scan_repository(REPO_PATH)
        ISSUES_REPORT = scan_issues(files)

    return ISSUES_REPORT


@app.get("/dependency-report")
def get_dependency_report():
    """Parsed dependency manifests enriched with known OSV.dev vulnerabilities
    (best-effort — falls back to a plain dependency list if offline)."""
    global DEPENDENCY_REPORT

    if DEPENDENCY_REPORT is None:
        files = scan_repository(REPO_PATH)
        DEPENDENCY_REPORT = generate_dependency_report(files)

    return DEPENDENCY_REPORT
