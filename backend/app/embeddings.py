from fastembed import TextEmbedding

model = TextEmbedding()


def create_embedding(text):
    return list(model.embed([text]))[0].tolist()


def embed_chunks(chunks):
    if not chunks:
        return []

    texts = [chunk["text"] for chunk in chunks]
    vectors = model.embed(texts, batch_size=32)  # batched, but bounded to keep memory use predictable

    return [
        {
            "text": chunk["text"],
            "metadata": chunk["metadata"],
            "embedding": vector.tolist(),
        }
        for chunk, vector in zip(chunks, vectors)
    ]

