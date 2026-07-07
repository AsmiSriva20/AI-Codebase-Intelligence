from fastapi import FastAPI
from pydantic import BaseModel
from git import Repo
from app.vectordb import store_embeddings,semantic_search

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

app = FastAPI()

# Stores embeddings in memory
EMBEDDED_CHUNKS = []


def analyze_repository(repo_path):

    repository_data = []

    files = scan_repository(repo_path)

    for file in files:

        if file["extension"] == ".py":

            result = analyze_file(file["full_path"])

            repository_data.append({
                "path": file["path"],
                "analysis": result
            })

    index = build_index(repository_data)

    chunks = chunk_repository(repository_data)

    global EMBEDDED_CHUNKS
    EMBEDDED_CHUNKS = embed_chunks(chunks)
    store_embeddings(EMBEDDED_CHUNKS)

    print("Chunks:", len(EMBEDDED_CHUNKS))

    return index


# Build the repository once when the server starts
INDEX = analyze_repository("repos/repository")


class RepoRequest(BaseModel):
    url: str

class SearchRequest(BaseModel):
    query: str


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

    results = semantic_search(request.query)

    return results