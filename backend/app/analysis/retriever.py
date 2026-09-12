from app.config import SEARCH_DEFAULT_N_RESULTS
from app.config import GRAPH_EXPANSION_RESULTS


def filter_results(results, max_results=SEARCH_DEFAULT_N_RESULTS):

    unique = set()
    filtered = []

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]

    for doc, meta in zip(documents, metadatas):

        key = (meta["path"], meta["name"])

        if key in unique:
            continue

        unique.add(key)

        filtered.append({
            "text": doc,
            "metadata": meta
        })

        if len(filtered) == max_results:
            break

    return filtered


def expand_with_call_graph(results, graph, load_analysis, max_results=GRAPH_EXPANSION_RESULTS):
    """Add source for direct callers/callees of retrieved Python symbols."""
    existing = {
        (item["metadata"].get("path"), item["metadata"].get("name"))
        for item in results
    }
    candidates = []
    for item in results:
        metadata = item["metadata"]
        if metadata.get("type") not in ("function", "class"):
            continue
        node = graph.get(f"{metadata.get('path')}::{metadata.get('name')}", {})
        related = [
            call["resolved"]
            for call in node.get("calls", [])
            if call.get("resolved")
        ] + node.get("called_by", [])
        candidates.extend(related)

    parsed_files = {}
    expanded = []
    for key in dict.fromkeys(candidates):
        if len(expanded) >= max_results or "::" not in key:
            break
        path, name = key.rsplit("::", 1)
        if name == "<module>" or (path, name) in existing:
            continue

        if path not in parsed_files:
            parsed_files[path] = load_analysis(path)
        analysis = parsed_files[path]
        if not analysis:
            continue

        function = next(
            (candidate for candidate in analysis.get("functions", []) if candidate.get("name") == name),
            None,
        )
        if function is None:
            continue

        expanded.append({
            "text": function.get("code", ""),
            "metadata": {
                "type": "function",
                "name": name,
                "path": path,
                "start_line": function.get("start_line"),
                "end_line": function.get("end_line"),
                "retrieval_methods": ["graph"],
                "retrieval_score": 0.5,
                "exact_match": False,
            },
        })
        existing.add((path, name))

    return results + expanded


def build_evidence(results):
    evidence = []
    for item in results:
        metadata = item["metadata"]
        path = metadata.get("path")
        if not path:
            continue
        start_line = metadata.get("start_line")
        end_line = metadata.get("end_line")
        citation = path
        if start_line:
            citation += f":{start_line}"
            if end_line and end_line != start_line:
                citation += f"-{end_line}"
        evidence.append({
            "path": path,
            "symbol": metadata.get("name"),
            "type": metadata.get("type"),
            "start_line": start_line,
            "end_line": end_line,
            "citation": citation,
            "retrieval_methods": metadata.get("retrieval_methods", []),
            "relevance": round(float(metadata.get("retrieval_score", 0)), 3),
        })
    return evidence


def retrieval_confidence(results):
    """Explainable retrieval confidence, not a probability of answer correctness."""
    if not results:
        return {
            "score": 0,
            "label": "low",
            "rationale": "No supporting code chunks were retrieved.",
        }

    methods = {
        method
        for item in results
        for method in item["metadata"].get("retrieval_methods", [])
    }
    exact_matches = sum(bool(item["metadata"].get("exact_match")) for item in results)
    top_score = max(float(item["metadata"].get("retrieval_score", 0)) for item in results)
    score = min(
        95,
        round(30 + min(len(results), 5) * 7 + len(methods) * 8 + exact_matches * 6 + top_score * 10),
    )
    label = "high" if score >= 75 else "medium" if score >= 50 else "low"
    rationale = (
        f"{len(results)} evidence chunks; retrieval used "
        f"{', '.join(sorted(methods)) or 'unknown'}; {exact_matches} exact lexical matches."
    )
    return {"score": score, "label": label, "rationale": rationale}
