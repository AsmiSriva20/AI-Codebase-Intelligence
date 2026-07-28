from fastembed import TextEmbedding, SparseTextEmbedding

from app.config import EMBEDDING_MODEL_NAME, SPARSE_EMBEDDING_MODEL_NAME, EMBEDDING_BATCH_SIZE

model = TextEmbedding(model_name=EMBEDDING_MODEL_NAME) if EMBEDDING_MODEL_NAME else TextEmbedding()
sparse_model = SparseTextEmbedding(model_name=SPARSE_EMBEDDING_MODEL_NAME)


def create_embedding(text):
    return list(model.embed([text]))[0].tolist()


def create_sparse_embedding(text):
    result = list(sparse_model.embed([text]))[0]
    return {"indices": result.indices.tolist(), "values": result.values.tolist()}


def embed_chunks_in_batches(chunks, batch_size=EMBEDDING_BATCH_SIZE):
    """Embed `chunks` and yield one embedded batch at a time instead of
    building the whole repo's dense+sparse vectors as a single in-memory list.
    A large repo can produce tens of thousands of chunks — holding all of their
    embeddings (plus a second copy for the Qdrant payload) at once is what was
    exceeding Render's 512MB limit, not the ONNX inference itself (which was
    already internally batched)."""
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start:start + batch_size]
        texts = [chunk["text"] for chunk in batch]
        vectors = list(model.embed(texts, batch_size=batch_size))
        sparse_vectors = list(sparse_model.embed(texts, batch_size=batch_size))

        yield [
            {
                "text": chunk["text"],
                "metadata": chunk["metadata"],
                "embedding": vector.tolist(),
                "sparse_embedding": {"indices": sparse.indices.tolist(), "values": sparse.values.tolist()},
            }
            for chunk, vector, sparse in zip(batch, vectors, sparse_vectors)
        ]
