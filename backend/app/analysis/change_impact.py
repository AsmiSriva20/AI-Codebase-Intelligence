"""Change-impact traversal over call and file-dependency graphs."""

from collections import deque

from app.analysis.callgraph import ENTRYPOINT_DECORATOR_SUFFIXES


def _is_test(key):
    path, _, name = key.partition("::")
    lowered = path.lower()
    return (
        name.lower().startswith("test_")
        or "/tests/" in f"/{lowered}"
        or lowered.startswith("tests/")
        or lowered.endswith("_test.py")
        or lowered.endswith(".test.js")
        or lowered.endswith(".test.ts")
    )


def _seed_symbols(graph, target):
    normalized = target.replace("\\", "/")
    if normalized in graph:
        return [normalized]
    if "::" in normalized:
        return [key for key in graph if key.lower() == normalized.lower()]

    file_matches = [key for key in graph if key.rsplit("::", 1)[0] == normalized]
    if file_matches:
        return file_matches
    return [key for key in graph if key.rsplit("::", 1)[-1].lower() == normalized.lower()]


def _traverse_callers(graph, seeds, max_depth):
    queue = deque((seed, 0) for seed in seeds)
    visited = set(seeds)
    impacted = {}
    while queue:
        current, depth = queue.popleft()
        if depth >= max_depth:
            continue
        for caller in graph.get(current, {}).get("called_by", []):
            if caller in visited:
                continue
            visited.add(caller)
            impacted[caller] = depth + 1
            queue.append((caller, depth + 1))
    return impacted


def _traverse_modules(architecture, paths, max_depth):
    reverse = {}
    for edge in architecture.get("edges", []):
        reverse.setdefault(edge["to"], []).append(edge["from"])

    queue = deque((path, 0) for path in paths)
    visited = set(paths)
    impacted = {}
    while queue:
        current, depth = queue.popleft()
        if depth >= max_depth:
            continue
        for dependent in reverse.get(current, []):
            if dependent in visited:
                continue
            visited.add(dependent)
            impacted[dependent] = depth + 1
            queue.append((dependent, depth + 1))
    return impacted


def analyze_change_impact(target, graph, architecture, definitions, max_depth=3):
    seeds = _seed_symbols(graph, target)
    normalized_target = target.replace("\\", "/")
    target_paths = {key.rsplit("::", 1)[0] for key in seeds}
    if normalized_target in architecture.get("nodes", []):
        target_paths.add(normalized_target)

    callers = _traverse_callers(graph, seeds, max_depth)
    modules = _traverse_modules(architecture, target_paths, max_depth)
    direct_callers = sorted(key for key, depth in callers.items() if depth == 1)
    transitive_callers = [
        {"symbol": key, "depth": depth}
        for key, depth in sorted(callers.items(), key=lambda item: (item[1], item[0]))
        if depth > 1
    ]

    impacted_symbols = set(seeds) | set(callers)
    endpoints = []
    tests = []
    evidence = []
    for key in sorted(impacted_symbols):
        definition = definitions.get(key, {})
        path, _, name = key.partition("::")
        decorators = definition.get("decorators", [])
        if any(decorator in ENTRYPOINT_DECORATOR_SUFFIXES for decorator in decorators):
            endpoints.append({
                "symbol": key,
                "decorators": decorators,
                "line": definition.get("line"),
            })
        if _is_test(key):
            tests.append({"symbol": key, "path": path, "line": definition.get("line")})
        evidence.append({
            "path": path,
            "symbol": name,
            "line": definition.get("line"),
            "reason": "changed target" if key in seeds else f"transitive caller at depth {callers[key]}",
        })

    risk_score = min(100, round(
        10
        + len(direct_callers) * 10
        + len(transitive_callers) * 5
        + len(modules) * 4
        + len(endpoints) * 10
    )) if (seeds or target_paths) else 0
    risk = "high" if risk_score >= 70 else "medium" if risk_score >= 35 else "low"

    return {
        "found": bool(seeds or target_paths),
        "target": target,
        "risk": risk,
        "risk_score": risk_score,
        "changed_symbols": sorted(seeds),
        "direct_callers": direct_callers,
        "transitive_callers": transitive_callers,
        "dependent_modules": [
            {"path": path, "depth": depth}
            for path, depth in sorted(modules.items(), key=lambda item: (item[1], item[0]))
        ],
        "affected_endpoints": endpoints,
        "affected_tests": tests,
        "evidence": evidence,
        "limitations": (
            "Call-level impact currently resolves Python symbols statically. File-level import impact "
            "also covers JavaScript/TypeScript; dynamic dispatch and runtime imports may be missed."
        ),
    }
