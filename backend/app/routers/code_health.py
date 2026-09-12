from fastapi import APIRouter, HTTPException

from app import state
from app.config import HOTSPOTS_DEFAULT_SINCE_DAYS
from app.schemas import ExplainRequest
from app.analysis.scanner import scan_repository
from app.analysis.issues import scan_repository as scan_issues
from app.analysis.dependency_scan import generate_dependency_report
from app.analysis.dead_code import find_dead_code
from app.analysis.architecture import generate_architecture
from app.analysis.architecture_health import analyze_architecture_health
from app.analysis.git_history import get_hotspots
from app.analysis.health_score import calculate_health_score
from app.llm.summary import summarize_repository
from app.llm.explainer import explain_file

router = APIRouter()


@router.get("/issues")
def get_issues(branch: str | None = None):
    """Repo-wide security & code-quality scan, cached until the next /clone or branch switch."""
    if branch:
        state.switch_to_branch(branch)  # resets ISSUES_REPORT if this actually changes the active branch

    if state.ISSUES_REPORT is None:
        files = scan_repository(state.REPO_PATH)
        state.ISSUES_REPORT = scan_issues(files)
        state.upsert_report(issues_report=state.ISSUES_REPORT)

    return state.ISSUES_REPORT


@router.get("/dependency-report")
def get_dependency_report(branch: str | None = None):
    """Parsed dependency manifests enriched with known OSV.dev vulnerabilities
    (best-effort — falls back to a plain dependency list if offline)."""
    if branch:
        state.switch_to_branch(branch)

    if state.DEPENDENCY_REPORT is None:
        files = scan_repository(state.REPO_PATH)
        state.DEPENDENCY_REPORT = generate_dependency_report(files)
        state.upsert_report(dependency_report=state.DEPENDENCY_REPORT)

    return state.DEPENDENCY_REPORT


@router.get("/dead-code")
def dead_code(branch: str | None = None):
    if branch:
        state.switch_to_branch(branch)

    if state.CURRENT_BRANCH_ID is None:
        raise HTTPException(status_code=400, detail="No repository cloned yet. Call /clone first.")

    if state.DEAD_CODE_REPORT is None:
        files = scan_repository(state.REPO_PATH)
        # Reuses the same cached call graph /call-graph and /ask rely on,
        # instead of re-parsing every file's AST a second time.
        state.DEAD_CODE_REPORT = find_dead_code(files, graph=state.get_call_graph())
        state.upsert_report(dead_code_report=state.DEAD_CODE_REPORT)

    return state.DEAD_CODE_REPORT


@router.get("/health-score")
def health_score(branch: str | None = None):
    if branch:
        state.switch_to_branch(branch)
    if state.CURRENT_BRANCH_ID is None:
        raise HTTPException(status_code=400, detail="No repository cloned yet. Call /clone first.")

    if state.HEALTH_SCORE_REPORT is None:
        files = scan_repository(state.REPO_PATH)
        issues_report = get_issues()
        dependency_report = get_dependency_report()
        dead_code_report = dead_code()

        if state.ARCHITECTURE_REPORT is None:
            state.ARCHITECTURE_REPORT = generate_architecture(files)
            state.upsert_report(architecture_report=state.ARCHITECTURE_REPORT)
        if state.ARCHITECTURE_HEALTH_REPORT is None:
            state.ARCHITECTURE_HEALTH_REPORT = analyze_architecture_health(
                state.ARCHITECTURE_REPORT
            )
            state.upsert_report(architecture_health_report=state.ARCHITECTURE_HEALTH_REPORT)
        if state.HOTSPOTS_REPORT is None:
            state.HOTSPOTS_REPORT = {
                "hotspots": get_hotspots(state.REPO_PATH, files),
                "since_days": HOTSPOTS_DEFAULT_SINCE_DAYS,
            }
            state.upsert_report(hotspots_report=state.HOTSPOTS_REPORT)

        state.HEALTH_SCORE_REPORT = calculate_health_score(
            issues_report,
            dependency_report,
            state.ARCHITECTURE_HEALTH_REPORT,
            dead_code_report,
            state.HOTSPOTS_REPORT,
        )
        state.upsert_report(health_score_report=state.HEALTH_SCORE_REPORT)

    return state.HEALTH_SCORE_REPORT


@router.get("/summary")
def repository_summary():
    if not state.FILES_INDEXED_COUNT:
        raise HTTPException(status_code=400, detail="No repository indexed yet. Import & build a repository first.")

    try:
        summary = summarize_repository(state.sample_repository_files())
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM request failed: {e}")

    return {"summary": summary}


@router.post("/explain-file")
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
