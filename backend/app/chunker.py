def chunk_repository(repository_data):
    chunks = []

    for file_data in repository_data:
        path = file_data["path"]
        analysis = file_data["analysis"]

        # Functions
        for function in analysis["functions"]:
            chunks.append({
                "text": f"Function: {function}",
                "metadata": {
                    "type": "function",
                    "name": function,
                    "path": path
                }
            })

        # Classes
        for cls in analysis["classes"]:
            chunks.append({
                "text": f"Class: {cls}",
                "metadata": {
                    "type": "class",
                    "name": cls,
                    "path": path
                }
            })

    return chunks