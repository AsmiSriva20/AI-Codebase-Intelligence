"""Every parser module/instance in this package exposes analyze_file(path) -> dict:

    functions: list[{"name": str, "code": str}]
    classes:   list[str]
    imports:   list[str]        # raw import/use/include statement text
    graph:     dict[str, list[str]]   # call graph; empty if not supported for this language

Downstream (indexer.py, search.py, chunker.py, callgraph.py) only depends on this
shape, not on how a given language produces it.
"""


def empty_analysis():
    return {"functions": [], "classes": [], "imports": [], "graph": {}}
