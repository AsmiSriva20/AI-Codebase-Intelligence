from app.config import EMBEDDING_MODEL_NAME, SPARSE_EMBEDDING_MODEL_NAME

_dense_model = None
_sparse_model = None


def _get_dense_model():
    """Importing fastembed at all (~60MB, pulls in onnxruntime/numpy) plus
    loading the dense model's ONNX weights (~85MB) is a big, fixed cost — on a
    memory-constrained host it shouldn't be paid by every process just for
    starting up, only by requests that actually need to embed something."""
    global _dense_model
    if _dense_model is None:
        from fastembed import TextEmbedding
        _dense_model = TextEmbedding(model_name=EMBEDDING_MODEL_NAME) if EMBEDDING_MODEL_NAME else TextEmbedding()
    return _dense_model


def _get_sparse_model():
    global _sparse_model
    if _sparse_model is None:
        from fastembed import SparseTextEmbedding
        _sparse_model = SparseTextEmbedding(model_name=SPARSE_EMBEDDING_MODEL_NAME)
    return _sparse_model


def create_embedding(text):
    return list(_get_dense_model().embed([text]))[0].tolist()


def create_sparse_embedding(text):
    result = list(_get_sparse_model().embed([text]))[0]
    return {"indices": result.indices.tolist(), "values": result.values.tolist()}


def embed_batch(batch):
    """Embed exactly one batch of chunks and return the embedded list. Kept
    separate from batching/looping logic so a streaming caller can build up
    one file at a time's worth of chunks and embed+flush as soon as a batch
    is full, instead of ever holding the whole repo's chunks in memory."""
    texts = [chunk["text"] for chunk in batch]
    vectors = list(_get_dense_model().embed(texts, batch_size=len(texts)))
    sparse_vectors = list(_get_sparse_model().embed(texts, batch_size=len(texts)))

    return [
        {
            "text": chunk["text"],
            "metadata": chunk["metadata"],
            "embedding": vector.tolist(),
            "sparse_embedding": {"indices": sparse.indices.tolist(), "values": sparse.values.tolist()},
        }
        for chunk, vector, sparse in zip(batch, vectors, sparse_vectors)
    ]
