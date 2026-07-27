import os
from app.config import REPO_PATH, SCAN_IGNORE_DIRS
from app.parsers import treesitter_parser
from app.analysis.indexer import build_index

def scan_repository(path):
    files = []

    for root, dirs, filenames in os.walk(path):

        # Skip ignored directories
        dirs[:] = [d for d in dirs if d not in SCAN_IGNORE_DIRS]

        for file in filenames:
            full_path = os.path.join(root, file)

            files.append({
                "path": os.path.relpath(full_path, path).replace("\\", "/"),
                "full_path": full_path,
                "extension": os.path.splitext(file)[1],
                "size": os.path.getsize(full_path)
            })

    return files


if __name__ == "__main__":

    files = scan_repository(REPO_PATH)

    repository_data = []

    for file in files:
        if file["extension"] == ".py":
         result = treesitter_parser.for_language("python").analyze_file(file["full_path"])

         repository_data.append({
                    "path": file["path"],
                    "analysis": result
                })
         
    index = build_index(repository_data)
    print(index)
    print(f"Analyzed {len(repository_data)} Python files.")