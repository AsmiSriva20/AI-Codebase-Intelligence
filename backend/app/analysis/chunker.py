from app.config import (
    CHUNK_WINDOW_LINES as WINDOW_LINES,
    CHUNK_MAX_TEXT_CHUNKS_PER_FILE as MAX_TEXT_CHUNKS_PER_FILE,
    CHUNK_MAX_CHARS as MAX_CHUNK_CHARS,
)


def _chunk_raw_text(text, path):
    chunks = []
    lines = text.split("\n")

    for start in range(0, len(lines), WINDOW_LINES):
        if len(chunks) >= MAX_TEXT_CHUNKS_PER_FILE:
            break

        window = "\n".join(lines[start:start + WINDOW_LINES]).strip()
        if not window:
            continue

        chunks.append({
            "text": window[:MAX_CHUNK_CHARS],
            "metadata": {
                "type": "text",
                "name": path,
                "path": path,
            },
        })

    return chunks


def chunk_repository(repository_data):
    chunks = []

    for file_data in repository_data:

        path = file_data["path"]
        analysis = file_data["analysis"]

        # Function chunks
        for function in analysis["functions"]:

            chunks.append({
                "text": function["code"][:MAX_CHUNK_CHARS],
                "metadata": {
                    "type": "function",
                    "name": function["name"],
                    "path": path,
                },
            })

        # Class chunks
        for cls in analysis["classes"]:

            chunks.append({
                "text": f"Class: {cls}",
                "metadata": {
                    "type": "class",
                    "name": cls,
                    "path": path,
                },
            })

        # Plain-text chunks (README, configs, docs, anything without code
        # structure) so semantic search / chat can answer questions that
        # aren't about a specific function or class.
        raw_text = analysis.get("raw_text")
        if raw_text and not analysis["functions"] and not analysis["classes"]:
            chunks.extend(_chunk_raw_text(raw_text, path))

    return chunks
