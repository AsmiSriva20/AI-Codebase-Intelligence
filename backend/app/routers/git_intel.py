from fastapi import APIRouter, HTTPException

from app import state
from app.config import HOTSPOTS_DEFAULT_SINCE_DAYS
from app.analysis.scanner import scan_repository
from app.analysis.git_history import get_file_history, get_hotspots

router = APIRouter()


@router.get("/file-history")
def file_history(path: str, branch: str | None = None):
    if branch:
        state.switch_to_branch(branch)
    try:
        return {"path": path, "history": get_file_history(state.REPO_PATH, path)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read history for '{path}': {e}")


@router.get("/hotspots")
def hotspots(branch: str | None = None, since_days: int = HOTSPOTS_DEFAULT_SINCE_DAYS):
    if branch:
        state.switch_to_branch(branch)

    if state.CURRENT_BRANCH_ID is None:
        raise HTTPException(status_code=400, detail="No repository cloned yet. Call /clone first.")

    # Cache invalidates on rebuild/branch-switch same as the other reports, but
    # also on a different since_days window — that changes the actual result.
    if state.HOTSPOTS_REPORT is None or state.HOTSPOTS_REPORT["since_days"] != since_days:
        files = scan_repository(state.REPO_PATH)
        state.HOTSPOTS_REPORT = {
            "hotspots": get_hotspots(state.REPO_PATH, files, since_days=since_days),
            "since_days": since_days,
        }
        state.upsert_report(hotspots_report=state.HOTSPOTS_REPORT)

    return state.HOTSPOTS_REPORT
