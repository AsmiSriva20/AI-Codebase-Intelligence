import ast

PY_EXTENSIONS = {".py"}


def _iter_functions(tree):
    """Yield every FunctionDef/AsyncFunctionDef in the tree, including
    methods nested inside classes and functions nested inside functions."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node


def build_call_graph(files):
    graph = {}

    for file_data in files:

        if file_data.get("extension") not in PY_EXTENSIONS:
            continue

        path = file_data["path"]
        full_path = file_data["full_path"]

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                source = f.read()

            tree = ast.parse(source)

        except (SyntaxError, UnicodeDecodeError, OSError):
            continue

        for node in _iter_functions(tree):

            calls = set()

            for child in ast.walk(node):

                if isinstance(child, ast.Call):

                    if isinstance(child.func, ast.Name):
                        calls.add(child.func.id)

                    elif isinstance(child.func, ast.Attribute):
                        calls.add(child.func.attr)

            # Key by "path::name" so same-named functions in different
            # files don't silently overwrite each other.
            key = f"{path}::{node.name}"
            graph[key] = sorted(calls)

    return graph


def find_function_calls(graph, function_name):
    """Look up calls for a function by short name, matching any file that
    defines it (returns the first match plus how many files defined it)."""
    matches = [key for key in graph if key.endswith(f"::{function_name}")]

    if not matches:
        return []

    return graph[matches[0]]
