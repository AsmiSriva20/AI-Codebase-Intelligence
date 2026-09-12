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
                "start_line": start + 1,
                "end_line": min(start + WINDOW_LINES, len(lines)),
            },
        })

    return chunks


def chunk_file(path, analysis):
    """Chunk one file's parsed analysis — called per-file by the streaming
    build so it never needs every file's analysis held in memory at once."""
    chunks = []

    # Function chunks
    for function in analysis["functions"]:

        chunks.append({
            "text": function["code"][:MAX_CHUNK_CHARS],
            "metadata": {
                "type": "function",
                "name": function["name"],
                "path": path,
                "start_line": function.get("start_line"),
                "end_line": function.get("end_line"),
            },
        })

    # Class chunks
    for cls in analysis["classes"]:

        location = analysis.get("class_locations", {}).get(cls, {})

        chunks.append({
            "text": f"Class: {cls}",
            "metadata": {
                "type": "class",
                "name": cls,
                "path": path,
                "start_line": location.get("start_line"),
                "end_line": location.get("end_line"),
            },
        })

    for block in analysis.get("blocks", []):
        chunks.append({
            "text": block["code"][:MAX_CHUNK_CHARS],
            "metadata": {
                "type": block["type"], "name": block["name"], "path": path,
                "start_line": block["start_line"], "end_line": block["end_line"],
            },
        })

    # Plain-text chunks (README, configs, docs, anything without code
    # structure) so semantic search / chat can answer questions that
    # aren't about a specific function or class.
    raw_text = analysis.get("raw_text")
    if raw_text and not analysis["functions"] and not analysis["classes"]:
        chunks.extend(_chunk_raw_text(raw_text, path))

    return chunks
