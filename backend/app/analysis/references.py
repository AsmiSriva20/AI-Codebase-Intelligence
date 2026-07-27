import ast


def find_references(files, function_name):

    references = []

    for file_data in files:

        path = file_data["full_path"]

        try:
            with open(path, "r", encoding="utf-8") as f:
                source = f.read()

            tree = ast.parse(source)

        except (SyntaxError, UnicodeDecodeError):
            continue

        for node in ast.walk(tree):

            if isinstance(node, ast.Call):

                # function()
                if isinstance(node.func, ast.Name):
                    if node.func.id == function_name:

                        references.append({
                            "file": file_data["path"],
                            "line": node.lineno,
                            "code": source.splitlines()[node.lineno - 1].strip()
                        })

                # module.function()
                elif isinstance(node.func, ast.Attribute):
                    if node.func.attr == function_name:

                        references.append({
                            "file": file_data["path"],
                            "line": node.lineno,
                            "code": source.splitlines()[node.lineno - 1].strip()
                        })

    return references