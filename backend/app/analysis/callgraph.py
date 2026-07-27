import ast
import re

from app.analysis.python_module_resolver import build_module_map, resolve_relative_import

PY_EXTENSIONS = {".py"}

ENTRYPOINT_NAME_RE = re.compile(r"^(main|__init__|test_.*|.*_test)$")
# Decorators that mean "called by a framework, not by any traceable in-repo call
# site" — these would otherwise all false-positive as dead code.
ENTRYPOINT_DECORATOR_SUFFIXES = {
    "route", "get", "post", "put", "delete", "patch", "options", "head",
    "websocket", "on_event", "middleware", "exception_handler", "fixture", "task",
}


def _iter_functions(tree):
    """Yield every FunctionDef/AsyncFunctionDef in the tree, including
    methods nested inside classes and functions nested inside functions."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node


def _iter_definitions(tree):
    """Yield every function/method/class definition in the tree."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            yield node


def _walk_skip_functions(node):
    """Like ast.walk, but doesn't descend into function bodies — those are
    already covered by build_call_graph's per-function pass. Surfaces calls
    made directly at module or class-body level, e.g. `app = FastAPI()` or
    `if __name__ == "__main__": main()`, which a purely per-function walk misses."""
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        yield child
        yield from _walk_skip_functions(child)


def _decorator_name(dec):
    """Best-effort dotted-suffix name for a decorator, e.g. @app.get(...) -> "get"."""
    target = dec.func if isinstance(dec, ast.Call) else dec
    if isinstance(target, ast.Attribute):
        return target.attr
    if isinstance(target, ast.Name):
        return target.id
    return None


def is_entrypoint(name, decorators):
    if ENTRYPOINT_NAME_RE.match(name):
        return True
    return any(d in ENTRYPOINT_DECORATOR_SUFFIXES for d in decorators)


def collect_definitions(files):
    """"path::name" -> {"type": "function"|"class", "decorators": [...], "line": int}
    for every function/method/class defined in the repo's Python files. Used by
    dead-code detection, alongside build_call_graph's "called_by" edges."""
    py_files = [f for f in files if f.get("extension") in PY_EXTENSIONS]
    definitions = {}

    for file_data in py_files:
        path = file_data["path"].replace("\\", "/")

        try:
            with open(file_data["full_path"], "r", encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError, OSError):
            continue

        for node in _iter_definitions(tree):
            key = f"{path}::{node.name}"
            decorators = [d for d in (_decorator_name(dec) for dec in node.decorator_list) if d]
            definitions[key] = {
                "type": "class" if isinstance(node, ast.ClassDef) else "function",
                "decorators": decorators,
                "line": node.lineno,
            }

    return definitions


def _collect_imports(tree, current_module):
    """local_name -> resolved dotted module string, for every name this file's
    imports bind into scope. Covers `import x.y`, `import x.y as z`,
    `from x.y import z`, `from x.y import z as w`, and relative imports."""
    imports = {}

    for node in ast.walk(tree):

        if isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name.split(".")[0]
                # Bare "import x.y" without "as" binds "x" as a module object;
                # accessing anything under it still goes through the full "x.y" path.
                imports[local] = alias.name if alias.asname else alias.name.split(".")[0]

        elif isinstance(node, ast.ImportFrom):
            base_module = resolve_relative_import(current_module, node.level, node.module)
            for alias in node.names:
                local = alias.asname or alias.name
                # `alias.name` is usually a function/class defined in base_module,
                # but could itself be a submodule (package import) — both are
                # tried at resolution time, see _resolve_call.
                imports[local] = f"{base_module}.{alias.name}" if base_module else alias.name

    return imports


def _dotted_chain(node):
    """Reconstruct the full dotted prefix of a Name/Attribute chain, e.g.
    `a.b.c` -> "a.b.c". Returns None if the chain doesn't bottom out in a plain Name
    (e.g. `foo().bar` — can't be resolved statically anyway)."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return None


def _resolve_call(call_node, current_path, current_module, defined_in_file, imports, module_map):
    """Best-effort resolution of a call site to a specific "path::function" — same-file
    calls and calls reachable through this file's own imports resolve; everything else
    (stdlib, third-party, calls through an object of unknown type) is left unresolved.
    """
    func = call_node.func

    if isinstance(func, ast.Name):
        name = func.id

        if name in defined_in_file.get(current_path, ()):
            return name, f"{current_path}::{name}"

        # `imports[name]` is "module.original_name" (see _collect_imports) — split
        # off the last segment as the real name in the target file, since that's
        # what it's defined as there even if this file imported it `as` something else.
        target_full = imports.get(name)
        if target_full:
            candidate_module, _, candidate_name = target_full.rpartition(".")
            target_path = module_map.get(candidate_module)
            if target_path and candidate_name in defined_in_file.get(target_path, ()):
                return name, f"{target_path}::{candidate_name}"

        return name, None

    if isinstance(func, ast.Attribute):
        chain = _dotted_chain(func)
        if chain is None:
            return func.attr, None

        base = chain.split(".")[0]
        method_name = func.attr

        # self.method() / cls.method() — heuristic: same file defines it.
        if base in ("self", "cls") and method_name in defined_in_file.get(current_path, ()):
            return chain, f"{current_path}::{method_name}"

        # Qualify the chain through this file's imports, e.g. `import x.y as z; z.func()`
        # rewrites the "z" prefix to "x.y", giving "x.y.func" — module="x.y", name="func".
        resolved_prefix = imports.get(base, base)
        rest = chain.split(".")[1:]
        chain_parts = resolved_prefix.split(".") + rest

        if len(chain_parts) >= 2:
            candidate_module = ".".join(chain_parts[:-1])
            candidate_name = chain_parts[-1]
            target_path = module_map.get(candidate_module)
            if target_path and candidate_name in defined_in_file.get(target_path, ()):
                return chain, f"{target_path}::{candidate_name}"

        return chain, None

    return None, None


def build_call_graph(files):
    """path::function -> {"calls": [{"name", "resolved"}], "called_by": [path::function, ...]}.

    "resolved" is a "path::function" string when the call could be traced to a
    definition in this repo (same file, or reachable via this file's own
    imports), and None for anything else (stdlib/third-party calls, or calls
    through an object whose type isn't known statically — this is a heuristic,
    not real type inference).
    """
    py_files = [f for f in files if f.get("extension") in PY_EXTENSIONS]
    module_map = build_module_map(py_files)

    # First pass: parse once per file, remember every function/method name it
    # defines (used for same-file resolution and as the target-side check for
    # cross-file resolution).
    parsed = {}
    defined_in_file = {}

    for file_data in py_files:
        path = file_data["path"].replace("\\", "/")
        full_path = file_data["full_path"]

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError, OSError):
            continue

        parsed[path] = tree
        # Includes classes, not just functions, so instantiation calls like
        # `Server()` resolve to the class definition below.
        defined_in_file[path] = {node.name for node in _iter_definitions(tree)}

    graph = {}

    # Second pass: resolve each call site now that defined_in_file covers every file.
    for path, tree in parsed.items():
        current_module = path[:-3].replace("/", ".")
        imports = _collect_imports(tree, current_module)

        # Pre-seed every class as a graph node (with no outgoing calls of its own)
        # so it can still receive "called_by" edges from wherever it's instantiated.
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                graph.setdefault(f"{path}::{node.name}", {"calls": [], "called_by": []})

        for node in _iter_functions(tree):
            calls = []
            seen = set()

            for child in ast.walk(node):
                if not isinstance(child, ast.Call):
                    continue

                name, resolved = _resolve_call(
                    child, path, current_module, defined_in_file, imports, module_map
                )
                if name is None:
                    continue

                dedupe_key = (name, resolved)
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                calls.append({"name": name, "resolved": resolved})

            key = f"{path}::{node.name}"
            graph.setdefault(key, {"calls": [], "called_by": []})
            graph[key]["calls"] = sorted(calls, key=lambda c: c["name"])

        # Calls made outside any function (module-level init, `if __name__ ==
        # "__main__":` blocks, class-body statements) still count as "used".
        module_calls = []
        seen = set()
        for child in _walk_skip_functions(tree):
            if not isinstance(child, ast.Call):
                continue

            name, resolved = _resolve_call(
                child, path, current_module, defined_in_file, imports, module_map
            )
            if name is None:
                continue

            dedupe_key = (name, resolved)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            module_calls.append({"name": name, "resolved": resolved})

        module_key = f"{path}::<module>"
        graph.setdefault(module_key, {"calls": [], "called_by": []})
        graph[module_key]["calls"] = sorted(module_calls, key=lambda c: c["name"])

    # Invert resolved edges into "called_by" so dead-code detection (zero
    # incoming edges) doesn't need to re-walk the whole graph itself.
    for caller_key, data in graph.items():
        for call in data["calls"]:
            if call["resolved"] and call["resolved"] in graph:
                graph[call["resolved"]]["called_by"].append(caller_key)

    for data in graph.values():
        data["called_by"] = sorted(set(data["called_by"]))

    return graph


def describe_relations(graph, path, name):
    """Human-readable "Calls: ... / Called by: ..." summary for a definition —
    lets a RAG context include cross-file relationships that a chunk's own text
    can't show on its own. Only resolved (in-repo) targets are listed; unresolved
    calls (stdlib/third-party/unknown-type objects) would be noise, not signal.
    Returns None if there's nothing resolved to say.
    """
    edges = graph.get(f"{path}::{name}")
    if not edges:
        return None

    lines = []
    calls = sorted({c["resolved"] for c in edges.get("calls", []) if c["resolved"]})
    if calls:
        lines.append(f"Calls: {', '.join(calls)}")
    called_by = edges.get("called_by", [])
    if called_by:
        lines.append(f"Called by: {', '.join(called_by)}")

    return "\n".join(lines) if lines else None


def find_function_calls(graph, function_name):
    """Look up calls for a function by short name, matching any file that
    defines it (returns the first match plus how many files defined it)."""
    matches = [key for key in graph if key.endswith(f"::{function_name}")]

    if not matches:
        return []

    return graph[matches[0]]["calls"]
