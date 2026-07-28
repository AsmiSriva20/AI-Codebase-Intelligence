import os
import time
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, SparseVectorParams, SparseVector, Modifier,
    PointStruct, Filter, FieldCondition, MatchValue, PayloadSchemaType,
    Prefetch, FusionQuery, Fusion,
)

from app.config import (
    QDRANT_COLLECTION as COLLECTION,
    QDRANT_TIMEOUT_SECONDS,
    QDRANT_VECTOR_SIZE as VECTOR_SIZE,
    QDRANT_UPSERT_BATCH_SIZE as UPSERT_BATCH_SIZE,
    QDRANT_UPSERT_MAX_RETRIES as UPSERT_MAX_RETRIES,
    DEFAULT_BRANCH_ID,
    SEARCH_DEFAULT_N_RESULTS,
    SEARCH_DENSE_ONLY_N_RESULTS,
)
from app.storage.embeddings import create_embedding, create_sparse_embedding

# Explicit, generous timeout: the library default is tuned for a single query,
# not a bulk upsert of every chunk's dense+sparse vectors in one request, which
# is a much bigger payload and was timing out on the default over a normal
# home connection.
client = QdrantClient(url=os.environ["QDRANT_URL"], api_key=os.environ["QDRANT_API_KEY"], timeout=QDRANT_TIMEOUT_SECONDS)
DENSE_VECTOR_NAME = "dense"
SPARSE_VECTOR_NAME = "sparse"


def _ensure_collection():
    if not client.collection_exists(COLLECTION):
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config={DENSE_VECTOR_NAME: VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)},
            # IDF modifier gives the BM25-style sparse vectors proper inverse-document-
            # frequency weighting server-side, rather than raw term-frequency scores.
            sparse_vectors_config={SPARSE_VECTOR_NAME: SparseVectorParams(modifier=Modifier.IDF)},
        )

    # Qdrant requires an index on any payload field used in a query/delete filter.
    # Idempotent: raises if the index already exists, which we can safely ignore.
    try:
        client.create_payload_index(
            collection_name=COLLECTION,
            field_name="branch_id",
            field_schema=PayloadSchemaType.KEYWORD,
        )
    except Exception:
        pass


def clear_branch(branch_id=DEFAULT_BRANCH_ID):
    """
    Remove all embeddings for a given branch (replaces the old clear_collection()).
    """
    _ensure_collection()
    client.delete(
        collection_name=COLLECTION,
        points_selector=Filter(must=[FieldCondition(key="branch_id", match=MatchValue(value=branch_id))]),
    )


def _upsert_with_retry(points):
    for attempt in range(1, UPSERT_MAX_RETRIES + 1):
        try:
            client.upsert(collection_name=COLLECTION, points=points)
            return
        except Exception as e:
            if attempt == UPSERT_MAX_RETRIES:
                raise
            print(f"Qdrant upsert attempt {attempt} failed ({e}); retrying...")
            time.sleep(2 * attempt)  # 2s, then 4s


def store_embeddings(batches, branch_id=DEFAULT_BRANCH_ID):
    """
    Store embedded chunks in Qdrant, scoped to branch_id. `batches` is an
    iterable of embedded-chunk lists (e.g. embed_chunks_in_batches) — each
    batch is converted and upserted as it arrives and then dropped, so peak
    memory is bounded by one batch instead of the whole repo's embeddings.
    Each point carries both a dense vector (semantic similarity) and a sparse
    BM25-style vector (keyword match) so hybrid_search can fuse the two.

    Returns (total_chunks_stored, embedding_dimension) so callers can report
    stats without needing to keep the embedded chunks around themselves.
    """
    clear_branch(branch_id)

    total = 0
    dimension = 0
    for batch in batches:
        if not batch:
            continue

        points = [
            PointStruct(
                # Qdrant point IDs must be an unsigned int or a UUID — a plain
                # "{branch_id}:{i}" string is rejected, and bare sequential ints
                # would collide across branches (IDs are unique per-collection,
                # not per-filter). Hash (branch_id, i) into a stable UUID instead.
                id=str(uuid.uuid5(uuid.NAMESPACE_OID, f"{branch_id}:{total + i}")),
                vector={
                    DENSE_VECTOR_NAME: chunk["embedding"],
                    SPARSE_VECTOR_NAME: SparseVector(**chunk["sparse_embedding"]),
                },
                payload={"branch_id": branch_id, "text": chunk["text"], **chunk["metadata"]},
            )
            for i, chunk in enumerate(batch)
        ]

        # Sub-batch again on the way to Qdrant — an embedding batch may still
        # be bigger than what's safe in a single upsert HTTP request — and
        # retrying absorbs any single transient failure instead of failing the
        # whole build over it.
        for start in range(0, len(points), UPSERT_BATCH_SIZE):
            _upsert_with_retry(points[start:start + UPSERT_BATCH_SIZE])

        if dimension == 0:
            dimension = len(batch[0]["embedding"])
        total += len(batch)

    if total:
        print("Stored embeddings:", collection_size(branch_id))

    return total, dimension


def collection_size(branch_id=DEFAULT_BRANCH_ID):
    """
    Return total number of embeddings for a branch.
    """
    _ensure_collection()
    count = client.count(
        collection_name=COLLECTION,
        count_filter=Filter(must=[FieldCondition(key="branch_id", match=MatchValue(value=branch_id))]),
    )
    return count.count


def _to_chroma_shape(query_response):
    """
    Reshape Qdrant's QueryResponse into the ChromaDB-style dict
    (`{"documents": [[...]], "metadatas": [[...]]}`) that retriever.py and
    main.py were already written against, so nothing downstream has to change.
    """
    documents, metadatas = [], []
    for point in query_response.points:
        payload = dict(point.payload)
        documents.append(payload.pop("text", ""))
        payload.pop("branch_id", None)
        metadatas.append(payload)

    return {"documents": [documents], "metadatas": [metadatas]}


def search_similar(query_embedding, n_results=SEARCH_DENSE_ONLY_N_RESULTS, branch_id=DEFAULT_BRANCH_ID):
    """
    Dense-only search using an already-created embedding.
    """
    results = client.query_points(
        collection_name=COLLECTION,
        query=query_embedding,
        using=DENSE_VECTOR_NAME,
        limit=n_results,
        query_filter=Filter(must=[FieldCondition(key="branch_id", match=MatchValue(value=branch_id))]),
    )
    return _to_chroma_shape(results)


def semantic_search(query, n_results=SEARCH_DEFAULT_N_RESULTS, branch_id=DEFAULT_BRANCH_ID):
    """
    Dense-only (semantic) search — kept for anything that just wants pure
    embedding similarity. /semantic-search and /ask use hybrid_search instead.
    """
    query_embedding = create_embedding(query)

    results = client.query_points(
        collection_name=COLLECTION,
        query=query_embedding,
        using=DENSE_VECTOR_NAME,
        limit=n_results,
        query_filter=Filter(must=[FieldCondition(key="branch_id", match=MatchValue(value=branch_id))]),
    )

    return _to_chroma_shape(results)


def hybrid_search(query, n_results=SEARCH_DEFAULT_N_RESULTS, branch_id=DEFAULT_BRANCH_ID):
    """
    Dense (semantic) + sparse (BM25-style keyword) search, fused server-side via
    Reciprocal Rank Fusion — this is why Qdrant was chosen over ChromaDB/pgvector
    in the DB migration: native hybrid search in one query, no second keyword-search
    system bolted on separately.
    """
    branch_filter = Filter(must=[FieldCondition(key="branch_id", match=MatchValue(value=branch_id))])
    dense_query = create_embedding(query)
    sparse_query = SparseVector(**create_sparse_embedding(query))

    results = client.query_points(
        collection_name=COLLECTION,
        prefetch=[
            Prefetch(query=dense_query, using=DENSE_VECTOR_NAME, filter=branch_filter, limit=n_results * 4),
            Prefetch(query=sparse_query, using=SPARSE_VECTOR_NAME, filter=branch_filter, limit=n_results * 4),
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        query_filter=branch_filter,
        limit=n_results,
    )

    return _to_chroma_shape(results)
