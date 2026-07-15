import ast


def build_call_graph(files):

    graph = {}

    for file_data in files:

        path = file_data["full_path"]

        try:
            with open(path, "r", encoding="utf-8") as f:
                source = f.read()

            tree = ast.parse(source)

        except (SyntaxError, UnicodeDecodeError):
            continue

        for node in tree.body:

            if isinstance(node, ast.FunctionDef):

                calls = set()

                for child in ast.walk(node):

                    if isinstance(child, ast.Call):

                        if isinstance(child.func, ast.Name):
                            calls.add(child.func.id)

                        elif isinstance(child.func, ast.Attribute):
                            calls.add(child.func.attr)

                graph[node.name] = sorted(list(calls))

    return graph