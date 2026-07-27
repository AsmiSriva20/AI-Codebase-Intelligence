from app.config import LLM_SUMMARY_MAX_FILES, LLM_SUMMARY_MAX_ITEMS_PER_FILE
from app.llm.client import ask_llm_json


def summarize_repository(repository_data):

    summary = ""

    for file_data in repository_data[:LLM_SUMMARY_MAX_FILES]:

        path = file_data["path"]
        analysis = file_data["analysis"]

        summary += f"\nFile: {path}\n"

        if analysis["functions"]:
            summary += "Functions:\n"
            for function in analysis["functions"][:LLM_SUMMARY_MAX_ITEMS_PER_FILE]:
                summary += f"- {function}\n"

        if analysis["classes"]:
            summary += "Classes:\n"
            for cls in analysis["classes"]:
                summary += f"- {cls}\n"

        if analysis["imports"]:
            summary += "Imports:\n"
            for imp in analysis["imports"][:LLM_SUMMARY_MAX_ITEMS_PER_FILE]:
                summary += f"- {imp}\n"

        summary += "\n"

    prompt = f"""
You are an expert software architect.

Analyze the following repository information and respond with a JSON object
(and nothing else) using exactly these keys:

- "purpose": string, 1-3 sentences on what this project does
- "frameworks": array of strings, frameworks and libraries used
- "main_modules": array of strings, the main files/modules and what each does
- "important_functions": array of strings, notable functions worth knowing about
- "architecture": string, a short paragraph on the overall architecture

Repository Information:

{summary}
"""

    return ask_llm_json(prompt)
