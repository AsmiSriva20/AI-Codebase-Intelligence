import ast
import os

from app import js_parser

JS_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
REPO_ROOT = os.path.join("repos", "repository")


def get_dependencies(path):
    full_path = os.path.join(REPO_ROOT, path)
    ext = os.path.splitext(path)[1].lower()

    if ext in JS_EXTENSIONS:
        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                return js_parser.get_imports(f.read())
        except OSError:
            return []

    imports = []

    try:
        with open(full_path, "r", encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source)

    except (SyntaxError, UnicodeDecodeError, OSError):
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
