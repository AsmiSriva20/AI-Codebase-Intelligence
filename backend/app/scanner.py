import os
from parser import analyze_file

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

        # Skip ignored directories
        dirs[:] = [d for d in dirs if d not in IGNORE]

        for file in filenames:
            full_path = os.path.join(root, file)

            files.append({
                "path": os.path.relpath(full_path, path),
                "full_path": full_path,
                "extension": os.path.splitext(file)[1],
                "size": os.path.getsize(full_path)
            })

    return files


if __name__ == "__main__":

    repo_path = "repos/repository"  

    files = scan_repository(repo_path)

    repository_data = []

    for file in files:
        if file["extension"] == ".py":
         result = analyze_file(file["full_path"])

         repository_data.append({
                    "path": file["path"],
                    "analysis": result
                })
    print(f"Analyzed {len(repository_data)} Python files.")