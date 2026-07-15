from fastapi import FastAPI
from pydantic import BaseModel
from git import Repo
from app.vectordb import store_embeddings, semantic_search
from app.llm import ask_llm

from app.scanner import scan_repository
from app.parser import analyze_file
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
from app.callgraph import build_call_graph
from app.dependency import get_dependencies
from app.architecture import generate_architecture

app = FastAPI()
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REPOSITORY_DATA = []
EMBEDDED_CHUNKS = []


def analyze_repository(repo_path):

    repository_data = []

    files = scan_repository(repo_path)

    for file in files:

        if file["extension"] == ".py":

            result = analyze_file(file["full_path"])

            repository_data.append(
                {
                    "path": file["path"],
                    "analysis": result,
                }
            )

    global REPOSITORY_DATA
    REPOSITORY_DATA = repository_data

    index = build_index(repository_data)

    chunks = chunk_repository(repository_data)

    global EMBEDDED_CHUNKS
    EMBEDDED_CHUNKS = embed_chunks(chunks)

    store_embeddings(EMBEDDED_CHUNKS)

    print("Chunks:", len(EMBEDDED_CHUNKS))

    return index


INDEX = None


# ---------------- Request Models ----------------

class RepoRequest(BaseModel):
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
    return {"message": "Backend Running 🚀"}


@app.post("/clone")
def clone_repo(repo: RepoRequest):

    Repo.clone_from(repo.url, "repos/repository")

    return {
        "message": "Repository cloned successfully!"
    }


@app.get("/scan")
def scan():

    files = scan_repository("repos/repository")

    return {
        "total_files": len(files),
        "files": files
    }


@app.get("/analyze")
def analyze():

    return {
        "chunks_created": len(EMBEDDED_CHUNKS),
        "embedding_dimension": len(EMBEDDED_CHUNKS[0]["embedding"]) if EMBEDDED_CHUNKS else 0
    }


@app.get("/function/{name}")
def search_function(name: str):

    return {
        "path": find_function(INDEX, name)
    }


@app.get("/class/{name}")
def search_class(name: str):

    return {
        "class": name,
        "path": find_class(INDEX, name)
    }


@app.get("/import/{name}")
def search_import(name: str):

    return {
        "import": name,
        "path": find_import(INDEX, name)
    }


@app.get("/calls/{name}")
def search_calls(name: str):

    return {
        "function": name,
        "calls": find_calls(INDEX, name)
    }


@app.post("/semantic-search")
def semantic_code_search(request: SearchRequest):

    return semantic_search(request.query)


@app.post("/ask")
def ask_repository(request: AskRequest):

    results = semantic_search(request.question)

    filtered = filter_results(results)

    context = ""

    for chunk in filtered:
        context += chunk["text"] + "\n\n"

    answer = ask_llm(
        request.question,
        context
    )

    return {
        "answer": answer,
        "sources": [chunk["metadata"] for chunk in filtered]
    }


@app.get("/summary")
def repository_summary():

    summary = summarize_repository(REPOSITORY_DATA)

    return {
        "summary": summary
    }


@app.post("/explain-file")
def explain(request: ExplainRequest):

    explanation = explain_file(request.path)

    return {
        "path": request.path,
        "explanation": explanation
    }

@app.post("/references")
def references(request: ReferenceRequest):

    files = scan_repository("repos/repository")

    result = find_references(
        files,
        request.function
    )

    return {
        "function": request.function,
        "references": result
    }

@app.post("/build")
def build_repository():

    global INDEX

    INDEX = analyze_repository("repos/repository")

    return {
        "message": "Repository indexed successfully",
        "chunks": len(EMBEDDED_CHUNKS)
    }

@app.post("/call-graph")
def call_graph(request: CallGraphRequest):

    files = scan_repository("repos/repository")

    graph = build_call_graph(files)

    return {
        "function": request.function,
        "calls": graph.get(request.function, [])
    }

@app.post("/dependencies")
def dependencies(request: DependencyRequest):

    imports = get_dependencies(request.path)

    return {
        "file": request.path,
        "dependencies": imports
    }

@app.get("/architecture")
def architecture():

    files = scan_repository("repos/repository")

    return generate_architecture(files)

class ArchitectureRequest(BaseModel):
    path: str


@app.post("/architecture")
def architecture_folder(request: ArchitectureRequest):

    files = scan_repository("repos/repository")

    return generate_architecture(
        files,
        request.path
    )