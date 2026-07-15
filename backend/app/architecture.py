import ast
import os


def generate_architecture(files, folder=None):

    if folder is not None:
        folder = folder.replace("\\", "/").rstrip("/")

    nodes = []
    edges = []
    edge_set = set()

    # Maps module names to actual repository files
    python_files = {}

    # ---------- First Pass: Collect all Python files ----------
    for file in files:

        if folder is not None:

            normalized = file["path"].replace("\\", "/")

            if not normalized.startswith(folder):
                continue

        if file["extension"] != ".py":
            continue

        path = file["path"].replace("\\", "/")

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

        if folder is not None:

            normalized = file["path"].replace("\\", "/")

            if not normalized.startswith(folder):
                continue

        if file["extension"] != ".py":
            continue

        path = file["path"].replace("\\", "/")
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

    return {
        "nodes": sorted(nodes),
        "edges": edges
    }