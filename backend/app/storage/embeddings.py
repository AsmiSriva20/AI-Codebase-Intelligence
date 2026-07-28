from fastembed import TextEmbedding, SparseTextEmbedding

from app.config import EMBEDDING_MODEL_NAME, SPARSE_EMBEDDING_MODEL_NAME

model = TextEmbedding(model_name=EMBEDDING_MODEL_NAME) if EMBEDDING_MODEL_NAME else TextEmbedding()
sparse_model = SparseTextEmbedding(model_name=SPARSE_EMBEDDING_MODEL_NAME)


def create_embedding(text):
    return list(model.embed([text]))[0].tolist()


def create_sparse_embedding(text):
    result = list(sparse_model.embed([text]))[0]
    return {"indices": result.indices.tolist(), "values": result.values.tolist()}


def embed_batch(batch):
    """Embed exactly one batch of chunks and return the embedded list. Kept
    separate from batching/looping logic so a streaming caller can build up
    one file at a time's worth of chunks and embed+flush as soon as a batch
    is full, instead of ever holding the whole repo's chunks in memory."""
    texts = [chunk["text"] for chunk in batch]
    vectors = list(model.embed(texts, batch_size=len(texts)))
    sparse_vectors = list(sparse_model.embed(texts, batch_size=len(texts)))

    return [
        {
            "text": chunk["text"],
            "metadata": chunk["metadata"],
            "embedding": vector.tolist(),
            "sparse_embedding": {"indices": sparse.indices.tolist(), "values": sparse.values.tolist()},
        }
        for chunk, vector, sparse in zip(batch, vectors, sparse_vectors)
    ]
