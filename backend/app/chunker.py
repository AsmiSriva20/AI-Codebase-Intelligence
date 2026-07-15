def chunk_repository(repository_data):
    chunks = []

    for file_data in repository_data:

        path = file_data["path"]
        analysis = file_data["analysis"]

        # Function chunks
        for function in analysis["functions"]:

            chunks.append({
                "text": function["code"],
                "metadata": {
                    "type": "function",
                    "name": function["name"],
                    "path": path
                }
            })

        # Class chunks
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