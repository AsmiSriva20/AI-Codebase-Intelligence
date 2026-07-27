"""Dead-code detection: functions/classes with zero incoming calls in the
call graph (callgraph.py), excluding known entrypoints.

This is a heuristic, not a guarantee:
- Dynamic dispatch (getattr, reflection, string-based lookup) isn't traceable
  by static analysis.
- Method calls through a variable of unknown type (`s = Server(); s.start()`)
  aren't resolved either — that needs real type inference, not just an AST walk.
- Only Python is analyzed today. Every other language's call graph is empty
  (see architecture.py's OTHER_LANGUAGE_EXTENSIONS notes for why), so this
  reports nothing for non-Python files rather than guessing.
"""
from app.analysis.callgraph import build_call_graph, collect_definitions, is_entrypoint

LIMITATION = (
    "Heuristic, not a guarantee: dynamic calls (getattr, reflection, string-based "
    "dispatch) and calls through a variable of unknown type (`obj.method()`) can't "
    "be traced by static analysis, and only Python is analyzed today — every other "
    "language isn't covered yet."
)


def find_dead_code(files, graph=None):
    if graph is None:
        graph = build_call_graph(files)
    definitions = collect_definitions(files)

    dead = []
    for key, meta in definitions.items():
        path, name = key.split("::", 1)

        if is_entrypoint(name, meta["decorators"]):
            continue

        if graph.get(key, {}).get("called_by"):
            continue

        dead.append({
            "path": path,
            "name": name,
            "type": meta["type"],
            "line": meta["line"],
        })

    dead.sort(key=lambda d: (d["path"], d["line"]))

    python_files_analyzed = len({f["path"] for f in files if f.get("extension") == ".py"})

    return {
        "dead_code": dead,
        "total_dead": len(dead),
        "python_files_analyzed": python_files_analyzed,
        "limitation": LIMITATION,
    }
