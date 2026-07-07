from fastembed import TextEmbedding

model = TextEmbedding()


def create_embedding(text):
    return list(model.embed([text]))[0].tolist()


def embed_chunks(chunks):
    embedded_chunks = []

    for chunk in chunks:
        embedded_chunks.append({
            "text": chunk["text"],
            "metadata": chunk["metadata"],
            "embedding": create_embedding(chunk["text"])
        })

    return embedded_chunks

