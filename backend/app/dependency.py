import ast
import os


def get_dependencies(path):
    full_path = os.path.join("repos/repository", path)

    imports = []

    try:
        with open(full_path, "r", encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source)

    except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
        return []

    for node in ast.walk(tree):

        # import os
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)

        # from app.scanner import scan_repository
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)

    return sorted(set(imports))