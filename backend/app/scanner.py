import os

IGNORE = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "venv",
    "__pycache__"
}

def scan_repository(path):
    files = []

    for root, dirs, filenames in os.walk(path):

        dirs[:] = [d for d in dirs if d not in IGNORE]

        for file in filenames:

            full_path = os.path.join(root, file)

            relative_path = os.path.relpath(full_path, path)

            extension = os.path.splitext(file)[1]

            size = os.path.getsize(full_path)

            files.append({
                "path": relative_path,
                "extension": extension,
                "size": size
            })

    return files