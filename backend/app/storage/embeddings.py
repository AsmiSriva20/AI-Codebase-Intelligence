from fastembed import TextEmbedding, SparseTextEmbedding

from app.config import EMBEDDING_MODEL_NAME, SPARSE_EMBEDDING_MODEL_NAME, EMBEDDING_BATCH_SIZE

model = TextEmbedding(model_name=EMBEDDING_MODEL_NAME) if EMBEDDING_MODEL_NAME else TextEmbedding()
sparse_model = SparseTextEmbedding(model_name=SPARSE_EMBEDDING_MODEL_NAME)


def create_embedding(text):
    return list(model.embed([text]))[0].tolist()


def create_sparse_embedding(text):
    result = list(sparse_model.embed([text]))[0]
    return {"indices": result.indices.tolist(), "values": result.values.tolist()}


def embed_chunks(chunks):
    if not chunks:
        return []

    texts = [chunk["text"] for chunk in chunks]
    vectors = model.embed(texts, batch_size=EMBEDDING_BATCH_SIZE)  # batched, but bounded to keep memory use predictable
    sparse_vectors = sparse_model.embed(texts, batch_size=EMBEDDING_BATCH_SIZE)

    return [
        {
            "text": chunk["text"],
            "metadata": chunk["metadata"],
            "embedding": vector.tolist(),
            "sparse_embedding": {"indices": sparse.indices.tolist(), "values": sparse.values.tolist()},
        }
        for chunk, vector, sparse in zip(chunks, vectors, sparse_vectors)
    ]
