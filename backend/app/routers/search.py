from fastapi import APIRouter, HTTPException

from app import state
from app.schemas import SearchRequest, AskRequest, ReferenceRequest, CallGraphRequest, DependencyRequest
from app.storage.vectordb import hybrid_search, collection_size
from app.llm.client import ask_llm
from app.analysis.indexer import find_function, find_class, find_import, find_calls
from app.analysis.retriever import (
    build_evidence,
    expand_with_call_graph,
    filter_results,
    retrieval_confidence,
)
from app.analysis.references import find_references
from app.analysis.callgraph import find_function_calls, describe_relations
from app.analysis.dependency import get_dependencies
from app.analysis.scanner import scan_repository

router = APIRouter()


@router.get("/function/{name}")
def search_function(name: str):
    state.require_index()
    return {"path": find_function(state.INDEX, name)}


@router.get("/class/{name}")
def search_class(name: str):
    state.require_index()
    return {"class": name, "path": find_class(state.INDEX, name)}


@router.get("/import/{name}")
def search_import(name: str):
    state.require_index()
    return {"import": name, "path": find_import(state.INDEX, name)}


@router.get("/calls/{name}")
def search_calls(name: str):
    state.require_index()
    return {"function": name, "calls": find_calls(state.INDEX, name)}


@router.post("/semantic-search")
def semantic_code_search(request: SearchRequest):
    branch_id = state.resolve_branch_id(request.branch)
    if collection_size(branch_id) == 0:
        raise HTTPException(status_code=400, detail="No repository indexed yet. Import & build a repository first.")
    return hybrid_search(request.query, branch_id=branch_id)


@router.post("/ask")
def ask_repository(request: AskRequest):
    branch_id = state.resolve_branch_id(request.branch)
    if collection_size(branch_id) == 0:
        raise HTTPException(status_code=400, detail="No repository indexed yet. Import & build a repository first.")

    results = hybrid_search(request.question, branch_id=branch_id)
    filtered = filter_results(results)

    # Retrieved chunks are isolated snippets — a function's own text can't show
    # that it calls (or is called by) something in a different file. Splicing
    # in the resolved call graph gives the LLM that cross-file context too.
    graph = state.get_call_graph() if any(c["metadata"].get("type") in ("function", "class") for c in filtered) else {}
    if graph:
        filtered = expand_with_call_graph(
            filtered,
            graph,
            state.get_relative_file_analysis,
        )

    context_parts = []
    for chunk in filtered:
        meta = chunk["metadata"]
        start_line = meta.get("start_line")
        end_line = meta.get("end_line")
        label = meta.get("path", "unknown")
        if start_line:
            label += f":{start_line}"
            if end_line and end_line != start_line:
                label += f"-{end_line}"
        context = f"SOURCE [{label}] ({meta.get('type', 'code')} {meta.get('name', '')})\n{chunk['text']}"
        if meta.get("type") in ("function", "class"):
            relations = describe_relations(graph, meta.get("path"), meta.get("name"))
            if relations:
                context += "\n" + relations
        context_parts.append(context)

    context = "\n\n".join(context_parts)

    try:
        answer = ask_llm(request.question, context)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM request failed: {e}")

    return {
        "answer": answer,
        "sources": [chunk["metadata"] for chunk in filtered],
        "evidence": build_evidence(filtered),
        "confidence": retrieval_confidence(filtered),
    }


@router.post("/references")
def references(request: ReferenceRequest):
    files = scan_repository(state.REPO_PATH)
    result = find_references(files, request.function)
    return {
        "function": request.function,
        "references": result,
    }


@router.post("/call-graph")
def call_graph(request: CallGraphRequest):
    graph = state.get_call_graph()
    return {
        "function": request.function,
        "calls": find_function_calls(graph, request.function),
    }


@router.post("/dependencies")
def dependencies(request: DependencyRequest):
    imports = get_dependencies(request.path)
    return {
        "file": request.path,
        "dependencies": imports,
    }
