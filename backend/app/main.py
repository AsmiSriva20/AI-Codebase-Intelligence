from fastapi import FastAPI
from pydantic import BaseModel
from git import Repo
from app.scanner import scan_repository
from app.indexer import build_index
from app.parser import analyze_file
from app.search import (
    find_function,
    find_class,
    find_import,
    find_calls,
)

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

    return build_index(repository_data)

app = FastAPI()
INDEX = analyze_repository("repos/repository")
class RepoRequest(BaseModel):
    url: str


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

    repo_path = "repos/repository"

    return analyze_repository(repo_path)

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
        "path": find_calls(INDEX, name)
    }