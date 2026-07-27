import os

from app.config import REPO_PATH, LLM_EXPLAIN_FILE_MAX_CHARS
from app.llm.client import ask_llm_json


def explain_file(relative_path):

    full_path = os.path.join(REPO_PATH, relative_path)

    try:
        with open(full_path, "r", encoding="utf-8") as f:
            code = f.read()[:LLM_EXPLAIN_FILE_MAX_CHARS]
    except OSError as e:
        raise FileNotFoundError(f"Could not read {relative_path}: {e}")

    prompt = f"""
You are an expert software engineer.

Analyze ONLY this file — do not explain the entire repository. Respond with
a JSON object (and nothing else) using exactly these keys:

- "purpose": string, purpose of the file
- "main_classes": array of strings
- "main_functions": array of strings
- "execution_flow": string, how execution proceeds through the file
- "important_logic": string, any notable or tricky logic worth calling out
- "external_dependencies": array of strings
- "summary": string, a short overall summary

File: {relative_path}

Code:
{code}
"""

    return ask_llm_json(prompt)
