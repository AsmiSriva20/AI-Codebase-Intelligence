from fastapi import FastAPI
from pydantic import BaseModel
from git import Repo
from app.scanner import scan_repository

app = FastAPI()


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