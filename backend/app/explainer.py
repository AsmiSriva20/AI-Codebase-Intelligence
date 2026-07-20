import os

from app.llm import ask_llm

REPO_ROOT = os.path.join("repos", "repository")


def explain_file(relative_path):

    full_path = os.path.join(REPO_ROOT, relative_path)

    try:
        with open(full_path, "r", encoding="utf-8") as f:
            code = f.read()[:8000]  # send only the first 8000 characters
    except OSError as e:
        raise FileNotFoundError(f"Could not read {relative_path}: {e}")

    prompt = f"""
You are an expert software engineer.

Analyze ONLY this file.

Explain:
1. Purpose of the file
2. Main classes
3. Main functions
4. Execution flow
5. Important logic
6. External dependencies
7. A short summary

Do not explain the entire repository.
Explain only this file.

File: {relative_path}

Code:
{code}
"""

    return ask_llm(prompt)
