import ast
import os

from app import js_parser

JS_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}


def _get_python_info(full_path, relative_path):
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source)

    except (SyntaxError, UnicodeDecodeError, OSError):
        return None

    functions = []
    classes = []
    imports = []

    docstring = ast.get_docstring(tree)

    for node in ast.walk(tree):

        if isinstance(node, ast.FunctionDef):
            functions.append(node.name)

        elif isinstance(node, ast.AsyncFunctionDef):
            functions.append(node.name)

        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)

        elif isinstance(node, ast.Import):

            for alias in node.names:
                imports.append(alias.name)

        elif isinstance(node, ast.ImportFrom):

            if node.module:
                imports.append(node.module)

    return {
        "path": relative_path,
        "language": "python",
        "functions": sorted(set(functions)),
        "classes": sorted(set(classes)),
        "imports": sorted(set(imports)),
        "docstring": docstring,
    }


def _get_js_info(full_path, relative_path):
    try:
        analysis = js_parser.analyze_file(full_path)
    except OSError:
        return None

    return {
        "path": relative_path,
        "language": "javascript",
        "functions": sorted({fn["name"] for fn in analysis["functions"]}),
        "classes": sorted(set(analysis["classes"])),
        "imports": sorted(set(analysis["imports"])),
        "docstring": None,
    }


def get_file_info(full_path, relative_path):
    ext = os.path.splitext(full_path)[1].lower()

    if ext == ".py":
        return _get_python_info(full_path, relative_path)

    if ext in JS_EXTENSIONS:
        return _get_js_info(full_path, relative_path)

    return {
        "path": relative_path,
        "language": ext.lstrip(".") or "unknown",
        "functions": [],
        "classes": [],
        "imports": [],
        "docstring": None,
        "unsupported": True,
    }
