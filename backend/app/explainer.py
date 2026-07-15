from app.llm import ask_llm


def explain_file(path):

    print("Requested path:", path)

    with open(path, "r", encoding="utf-8") as f:
        code = f.read()[:8000]   # send only the first 8000 characters

    print("First 300 chars:\n")
    print(code[:300])

    prompt = f"""
You are an expert Python software engineer.

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

Code:
{code}
"""

    return ask_llm(prompt)