"""Every parser module/instance in this package exposes analyze_file(path) -> dict:

    functions: list[{"name": str, "code": str, "start_line": int, "end_line": int}]
    classes:   list[str]
    class_locations: dict[str, {"start_line": int, "end_line": int}]
    imports:   list[str]        # raw import/use/include statement text
    graph:     dict[str, list[str]]   # call graph; empty if not supported for this language
    blocks:    optional list[{"type": str, "name": str, "code": str,
                              "start_line": int, "end_line": int}]
    raw_text:  optional str, retained for configuration context in search

Downstream (indexer.py, search.py, chunker.py, callgraph.py) only depends on this
shape, not on how a given language produces it.
"""


def empty_analysis():
    return {"functions": [], "classes": [], "class_locations": {}, "imports": [], "graph": {}}
