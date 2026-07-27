"""Shared Python module<->file resolution, used by both architecture.py (file-level
import edges) and callgraph.py (function-level call resolution) so the two don't
maintain two independent copies of the same dotted-module-name math.
"""


def build_module_map(files):
    """path or dotted-module-name -> file path, for every .py file in `files`.

    Example: "src/app/main.py" is reachable both as itself and as "src.app.main".
    """
    module_map = {}

    for file in files:
        path = file["path"].replace("\\", "/")

        if file["extension"] != ".py":
            continue

        module_map[path] = path

        module_name = path[:-3].replace("/", ".")
        module_map[module_name] = path

    return module_map


def resolve_relative_import(current_module, level, module):
    """Mirror Python's relative-import resolution (`from . import x`, `from ..y import z`)."""
    if level == 0:
        return module or ""

    base = current_module.split(".")[:-level]

    if module:
        return ".".join(base + module.split("."))
    return ".".join(base)
