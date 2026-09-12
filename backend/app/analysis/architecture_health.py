"""Deterministic architecture-governance checks over the repository file graph."""

from collections import defaultdict

from app.config import ARCHITECTURE_HIGH_COUPLING_THRESHOLD


LAYER_ORDER = {
    "presentation": 0,
    "controller": 1,
    "service": 2,
    "repository": 3,
    "database": 4,
}


def infer_layer(path):
    normalized_path = path.replace("\\", "/").lower()
    normalized = f"/{normalized_path}/"
    # Order matters: a router called repository.py is still a controller.
    if any(part in normalized for part in ("/frontend/", "/ui/", "/components/", "/views/")):
        return "presentation"
    if any(part in normalized for part in ("/controllers/", "/controller/", "/routers/", "/routes/")):
        return "controller"
    if any(part in normalized for part in ("/services/", "/service/", "/usecases/", "/use_cases/")):
        return "service"
    if any(part in normalized for part in ("/repositories/", "/repository/", "/dao/")):
        return "repository"
    if any(part in normalized for part in ("/database/", "/db/", "/storage/", "/models/")):
        return "database"
    return None


def _strongly_connected_components(nodes, edges):
    adjacency = defaultdict(list)
    for edge in edges:
        adjacency[edge["from"]].append(edge["to"])

    index = 0
    indices = {}
    lowlinks = {}
    stack = []
    on_stack = set()
    components = []

    def visit(node):
        nonlocal index
        indices[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)

        for target in adjacency[node]:
            if target not in indices:
                visit(target)
                lowlinks[node] = min(lowlinks[node], lowlinks[target])
            elif target in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[target])

        if lowlinks[node] == indices[node]:
            component = []
            while True:
                member = stack.pop()
                on_stack.remove(member)
                component.append(member)
                if member == node:
                    break
            if len(component) > 1 or node in adjacency[node]:
                components.append(sorted(component))

    for node in nodes:
        if node not in indices:
            visit(node)
    return sorted(components)


def analyze_architecture_health(architecture):
    nodes = architecture.get("nodes", [])
    edges = architecture.get("edges", [])
    violations = []
    incoming = defaultdict(int)
    outgoing = defaultdict(int)

    for edge in edges:
        source = edge["from"]
        target = edge["to"]
        outgoing[source] += 1
        incoming[target] += 1
        source_layer = infer_layer(source)
        target_layer = infer_layer(target)
        if source_layer is None or target_layer is None:
            continue

        source_rank = LAYER_ORDER[source_layer]
        target_rank = LAYER_ORDER[target_layer]
        if target_rank < source_rank:
            violations.append({
                "type": "reverse-layer-dependency",
                "from": source,
                "to": target,
                "message": f"{source_layer} depends upward on {target_layer}",
            })
        elif target_rank > source_rank + 1:
            violations.append({
                "type": "skipped-layer",
                "from": source,
                "to": target,
                "message": f"{source_layer} bypasses {target_layer} boundaries",
            })

    cycles = [
        {"nodes": component, "size": len(component)}
        for component in _strongly_connected_components(nodes, edges)
    ]
    high_coupling = []
    for node in nodes:
        fan_in = incoming[node]
        fan_out = outgoing[node]
        total = fan_in + fan_out
        if total >= ARCHITECTURE_HIGH_COUPLING_THRESHOLD:
            high_coupling.append({
                "path": node,
                "fan_in": fan_in,
                "fan_out": fan_out,
                "coupling": total,
            })
    high_coupling.sort(key=lambda item: item["coupling"], reverse=True)

    return {
        "summary": {
            "layer_violations": len(violations),
            "circular_dependencies": len(cycles),
            "high_coupling_modules": len(high_coupling),
        },
        "layer_violations": violations,
        "circular_dependencies": cycles,
        "high_coupling_modules": high_coupling,
        "rules": {
            "layer_order": list(LAYER_ORDER),
            "high_coupling_threshold": ARCHITECTURE_HIGH_COUPLING_THRESHOLD,
        },
    }
