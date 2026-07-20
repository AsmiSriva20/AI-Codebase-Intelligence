import ast
import os
import re


JS_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
JS_RESOLVE_EXTENSIONS = [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".json"]

# Matches: import x from '...'; export {a} from '...'; export * from '...'
JS_FROM_RE = re.compile(r"""from\s+['"]([^'"]+)['"]""")
# Matches: require('...')
JS_REQUIRE_RE = re.compile(r"""\brequire\(\s*['"]([^'"]+)['"]\s*\)""")
# Matches: import('...')  (dynamic import)
JS_DYNAMIC_IMPORT_RE = re.compile(r"""\bimport\(\s*['"]([^'"]+)['"]\s*\)""")
# Matches side-effect imports: import '...'
JS_BARE_IMPORT_RE = re.compile(r"""\bimport\s+['"]([^'"]+)['"]""")


def _in_folder_scope(path, folder):
    if folder is None:
        return True
    return path.startswith(folder)


def _generate_python_graph(files, folder):
    nodes = []
    edges = []
    edge_set = set()

    # Maps module names to actual repository files
    python_files = {}

    # ---------- First Pass: Collect all Python files ----------
    for file in files:

        path = file["path"].replace("\\", "/")

        if not _in_folder_scope(path, folder):
            continue

        if file["extension"] != ".py":
            continue

        nodes.append(path)

        # Map file path
        python_files[path] = path

        # Map module name
        # Example:
        # src/flask/app.py -> src.flask.app
        module_name = path[:-3].replace("/", ".")
        python_files[module_name] = path

    # ---------- Second Pass: Build Dependency Graph ----------
    for file in files:

        path = file["path"].replace("\\", "/")

        if not _in_folder_scope(path, folder):
            continue

        if file["extension"] != ".py":
            continue

        full_path = file["full_path"]

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                source = f.read()

            tree = ast.parse(source)

        except Exception:
            continue

        current_module = path[:-3].replace("/", ".")
        current_parts = current_module.split(".")

        for node in ast.walk(tree):

            # -------- from ... import --------
            if isinstance(node, ast.ImportFrom):

                module = node.module or ""

                if node.level == 0:
                    target_module = module
                else:
                    base = current_parts[:-node.level]

                    if module:
                        target_module = ".".join(base + module.split("."))
                    else:
                        target_module = ".".join(base)

                target = python_files.get(target_module)

                if target:

                    edge = (path, target)

                    if edge not in edge_set:
                        edge_set.add(edge)

                        edges.append({
                            "from": path,
                            "to": target
                        })

            # -------- import --------
            elif isinstance(node, ast.Import):

                for alias in node.names:

                    target = python_files.get(alias.name)

                    if target:

                        edge = (path, target)

                        if edge not in edge_set:
                            edge_set.add(edge)

                            edges.append({
                                "from": path,
                                "to": target
                            })

    return nodes, edges


def _resolve_js_specifier(current_path, specifier, valid_paths):
    # Only follow relative/rooted imports; skip bare package specifiers (npm deps).
    if not (specifier.startswith(".") or specifier.startswith("/")):
        return None

    if specifier.startswith("/"):
        base = specifier.lstrip("/")
    else:
        current_dir = os.path.dirname(current_path)
        base = os.path.normpath(os.path.join(current_dir, specifier)).replace("\\", "/")

    if base in valid_paths:
        return valid_paths[base]

    for ext in JS_RESOLVE_EXTENSIONS:
        candidate = base + ext
        if candidate in valid_paths:
            return valid_paths[candidate]

    for ext in JS_RESOLVE_EXTENSIONS:
        candidate = f"{base}/index{ext}"
        if candidate in valid_paths:
            return valid_paths[candidate]

    return None


def _generate_js_graph(files, folder):
    nodes = []
    edges = []
    edge_set = set()

    # Maps normalized file path -> actual repository file path
    js_files = {}

    # ---------- First Pass: Collect all JS/TS files ----------
    for file in files:

        path = file["path"].replace("\\", "/")

        if not _in_folder_scope(path, folder):
            continue

        if file["extension"] not in JS_EXTENSIONS:
            continue

        nodes.append(path)
        js_files[path] = path

    # ---------- Second Pass: Build Dependency Graph ----------
    for file in files:

        path = file["path"].replace("\\", "/")

        if not _in_folder_scope(path, folder):
            continue

        if file["extension"] not in JS_EXTENSIONS:
            continue

        full_path = file["full_path"]

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                source = f.read()
        except Exception:
            continue

        specifiers = set()
        specifiers.update(JS_FROM_RE.findall(source))
        specifiers.update(JS_REQUIRE_RE.findall(source))
        specifiers.update(JS_DYNAMIC_IMPORT_RE.findall(source))
        specifiers.update(JS_BARE_IMPORT_RE.findall(source))

        for specifier in specifiers:

            target = _resolve_js_specifier(path, specifier, js_files)

            if target and target != path:

                edge = (path, target)

                if edge not in edge_set:
                    edge_set.add(edge)

                    edges.append({
                        "from": path,
                        "to": target
                    })

    return nodes, edges


def generate_architecture(files, folder=None):

    if folder is not None:
        folder = folder.replace("\\", "/").rstrip("/")

    py_nodes, py_edges = _generate_python_graph(files, folder)
    js_nodes, js_edges = _generate_js_graph(files, folder)

    return {
        "nodes": sorted(set(py_nodes) | set(js_nodes)),
        "edges": py_edges + js_edges
    }
