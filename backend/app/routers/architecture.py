import os

from fastapi import APIRouter, HTTPException

from app import state
from app.schemas import ArchitectureRequest
from app.analysis.scanner import scan_repository
from app.analysis.architecture import generate_architecture
from app.analysis.file_info import get_file_info

router = APIRouter()


@router.get("/architecture")
def architecture(branch: str | None = None):
    if branch:
        state.switch_to_branch(branch)

    # Only the unscoped (whole-repo) view is cached — a folder-scoped view is
    # just a filter over the same parse, and there are unboundedly many possible
    # scopes, so caching each one isn't practical.
    if state.ARCHITECTURE_REPORT is None:
        files = scan_repository(state.REPO_PATH)
        state.ARCHITECTURE_REPORT = generate_architecture(files)
        state.upsert_report(architecture_report=state.ARCHITECTURE_REPORT)

    return state.ARCHITECTURE_REPORT


@router.post("/architecture")
def architecture_folder(request: ArchitectureRequest):
    if request.branch:
        state.switch_to_branch(request.branch)
    files = scan_repository(state.REPO_PATH)
    return generate_architecture(files, request.path)


@router.get("/file-info")
def file_info(path: str):
    files = scan_repository(state.REPO_PATH)

    for file in files:
        if file["path"] == path:
            result = get_file_info(file["full_path"], file["path"])

            if result is None:
                raise HTTPException(status_code=400, detail="Unable to parse file.")

            return result

    raise HTTPException(status_code=404, detail="File not found.")


@router.get("/file-content")
def get_file_content(path: str):
    candidates = [path, os.path.join(state.REPO_PATH, path)]
    resolved = next((c for c in candidates if os.path.exists(c)), None)

    if resolved is None:
        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    try:
        with open(resolved, "r", encoding="utf-8") as f:
            content = f.read()
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
