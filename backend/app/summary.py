from app.llm import ask_llm


def summarize_repository(repository_data):

    summary = ""

    for file_data in repository_data[:20]:

        path = file_data["path"]
        analysis = file_data["analysis"]

        summary += f"\nFile: {path}\n"

        if analysis["functions"]:
            summary += "Functions:\n"
            for function in analysis["functions"][:3]:
                summary += f"- {function}\n"

        if analysis["classes"]:
            summary += "Classes:\n"
            for cls in analysis["classes"]:
                summary += f"- {cls}\n"

        if analysis["imports"]:
            summary += "Imports:\n"
            for imp in analysis["imports"][:3]:
                summary += f"- {imp}\n"

        summary += "\n"

    prompt = f"""
You are an expert software architect.

Analyze the following repository information and write a concise summary.

Include:
- Purpose of the project
- Frameworks and libraries used
- Main modules
- Important functions
- Overall architecture

Repository Information:

{summary}



Repository Summary:
"""

    return ask_llm(prompt)