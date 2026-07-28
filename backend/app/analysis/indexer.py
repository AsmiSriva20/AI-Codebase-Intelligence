def find_function(index, name):
    return index["functions"].get(name)


def find_class(index, name):
    return index["classes"].get(name)


def find_import(index, module):
    return index["imports"].get(module)


def find_calls(index, function):
    return index["call_graph"].get(function)


def empty_index():
    return {
        "functions": {},
        "classes": {},
        "imports": {},
        "call_graph": {},
    }


def index_file(index, path, analysis):
    """Fold one file's parsed analysis into `index` in place — split out of
    build_index so a streaming build can index one file at a time instead of
    needing every file's analysis held in memory at once."""

    # Index functions
    for function in analysis["functions"]:
        index["functions"][function["name"]] = path

    # Index classes
    for cls in analysis["classes"]:
        index["classes"][cls] = path

    # Index imports
    for imp in analysis["imports"]:
        if imp not in index["imports"]:
            index["imports"][imp] = []

        index["imports"][imp].append(path)

    for function, calls in analysis["graph"].items():
        index["call_graph"][function] = calls


def build_index(repository_data):
    index = empty_index()
    for file_data in repository_data:
        index_file(index, file_data["path"], file_data["analysis"])
    return index