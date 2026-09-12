from collections import Counter
import hashlib
import math
import os
import re
import time
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams,
    PointStruct, Filter, FieldCondition, MatchAny, MatchValue, PayloadSchemaType,
)

from app.config import (
    QDRANT_COLLECTION as COLLECTION,
    QDRANT_TIMEOUT_SECONDS,
    QDRANT_VECTOR_SIZE as VECTOR_SIZE,
    QDRANT_UPSERT_BATCH_SIZE as UPSERT_BATCH_SIZE,
    QDRANT_UPSERT_MAX_RETRIES as UPSERT_MAX_RETRIES,
    DEFAULT_BRANCH_ID,
    HYBRID_DENSE_CANDIDATES,
    HYBRID_LEXICAL_CANDIDATES,
    LEXICAL_SCAN_LIMIT,
    SEARCH_DEFAULT_N_RESULTS,
    SEARCH_DENSE_ONLY_N_RESULTS,
)
from app.storage.embeddings import create_embedding

# Explicit, generous timeout: the library default is tuned for a single query,
# not a bulk upsert of every chunk's dense vectors in one request, which
# is a much bigger payload and was timing out on the default over a normal
# home connection.
client = QdrantClient(url=os.environ["QDRANT_URL"], api_key=os.environ["QDRANT_API_KEY"], timeout=QDRANT_TIMEOUT_SECONDS)
DENSE_VECTOR_NAME = "dense"
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]*|[0-9]+")


def _ensure_collection():
    if not client.collection_exists(COLLECTION):
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config={DENSE_VECTOR_NAME: VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)},
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


def delete_files(branch_id, paths):
    """Delete every vector belonging to the supplied repository-relative paths."""
    paths = sorted({path.replace("\\", "/") for path in paths if path})
    if not paths:
        return
    _ensure_collection()
    client.delete(
        collection_name=COLLECTION,
        points_selector=Filter(must=[
            FieldCondition(key="branch_id", match=MatchValue(value=branch_id)),
            FieldCondition(key="path", match=MatchAny(any=paths)),
        ]),
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


def store_embeddings(batches, branch_id=DEFAULT_BRANCH_ID, clear_existing=True):
    """
    Store embedded chunks in Qdrant, scoped to branch_id. `batches` is an
    iterable of embedded-chunk lists (e.g. embed_chunks_in_batches) — each
    batch is converted and upserted as it arrives and then dropped, so peak
    memory is bounded by one batch instead of the whole repo's embeddings.
    Each point carries the dense semantic vector returned by OpenAI.

    Returns (total_chunks_stored, embedding_dimension) so callers can report
    stats without needing to keep the embedded chunks around themselves.
    """
    if clear_existing:
        clear_branch(branch_id)

    total = 0
    dimension = 0
    for batch in batches:
        if not batch:
            continue

        points = [
            PointStruct(
                # Stable per-chunk UUIDs let incremental builds replace only
                # vectors for changed paths without renumbering a whole branch.
                id=str(uuid.uuid5(
                    uuid.NAMESPACE_OID,
                    ":".join([
                        str(branch_id),
                        chunk.get("metadata", {}).get("path", ""),
                        chunk.get("metadata", {}).get("type", ""),
                        chunk.get("metadata", {}).get("name", ""),
                        str(chunk.get("metadata", {}).get("start_line", "")),
                        hashlib.sha256(chunk["text"].encode("utf-8")).hexdigest(),
                    ]),
                )),
                vector={
                    DENSE_VECTOR_NAME: chunk["embedding"],
                },
                payload={
                    "branch_id": branch_id,
                    "text": chunk["text"],
                    **{key: value for key, value in chunk["metadata"].items() if value is not None},
                },
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


def _to_chroma_shape(query_response, retrieval_method="dense"):
    """
    Reshape Qdrant's QueryResponse into the ChromaDB-style dict
    (`{"documents": [[...]], "metadatas": [[...]]}`) that retriever.py and
    main.py were already written against, so nothing downstream has to change.
    """
    documents, metadatas, scores = [], [], []
    for point in query_response.points:
        payload = dict(point.payload)
        documents.append(payload.pop("text", ""))
        payload.pop("branch_id", None)
        payload["retrieval_methods"] = [retrieval_method]
        payload["retrieval_score"] = float(point.score or 0)
        metadatas.append(payload)
        scores.append(float(point.score or 0))

    return {"documents": [documents], "metadatas": [metadatas], "scores": [scores]}


def _tokenize(value):
    """Tokenize identifiers, paths, and prose while retaining useful code names."""
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value or "")
    return [match.group(0).lower() for match in TOKEN_RE.finditer(value)]


def _scroll_branch(branch_id, limit=LEXICAL_SCAN_LIMIT):
    records = []
    offset = None
    while len(records) < limit:
        page, offset = client.scroll(
            collection_name=COLLECTION,
            scroll_filter=Filter(must=[
                FieldCondition(key="branch_id", match=MatchValue(value=branch_id)),
            ]),
            limit=min(256, limit - len(records)),
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        records.extend(page)
        if offset is None or not page:
            break
    return records


def _lexical_rank(query, branch_id, limit=HYBRID_LEXICAL_CANDIDATES):
    """Rank stored chunks with BM25 plus exact path/symbol boosts."""
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    records = _scroll_branch(branch_id)
    if not records:
        return []

    tokenized = []
    document_frequency = Counter()
    for record in records:
        payload = record.payload or {}
        # Repeated path/name terms make code identifiers more influential than
        # incidental prose occurrences without requiring another service.
        searchable = " ".join([
            payload.get("path", ""), payload.get("path", ""),
            payload.get("name", ""), payload.get("name", ""),
            payload.get("text", ""),
        ])
        tokens = _tokenize(searchable)
        tokenized.append((record, tokens, searchable.lower()))
        document_frequency.update(set(tokens))

    average_length = sum(len(tokens) for _, tokens, _ in tokenized) / len(tokenized)
    query_phrase = (query or "").strip().lower()
    ranked = []
    for record, tokens, searchable in tokenized:
        frequencies = Counter(tokens)
        score = 0.0
        for token in query_tokens:
            frequency = frequencies[token]
            if not frequency:
                continue
            frequency_docs = document_frequency[token]
            inverse_document_frequency = math.log(
                1 + (len(tokenized) - frequency_docs + 0.5) / (frequency_docs + 0.5)
            )
            normalization = frequency + 1.2 * (
                1 - 0.75 + 0.75 * len(tokens) / max(average_length, 1)
            )
            score += inverse_document_frequency * (frequency * 2.2) / normalization

        exact_match = bool(query_phrase and query_phrase in searchable)
        if exact_match:
            score += 2.0
        if score > 0:
            ranked.append((record, score, exact_match))

    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked[:limit]


def _hybrid_shape(dense_points, lexical_points, n_results):
    """Fuse semantic and BM25 rankings with weighted reciprocal-rank fusion."""
    combined = {}
    ranking_groups = (
        ("semantic", 0.60, [(point, False) for point in dense_points]),
        ("lexical", 0.40, [(point, exact) for point, _score, exact in lexical_points]),
    )

    for method, weight, ranked in ranking_groups:
        for rank, (point, exact_match) in enumerate(ranked, start=1):
            key = str(point.id)
            entry = combined.setdefault(key, {
                "point": point,
                "score": 0.0,
                "methods": [],
                "exact_match": False,
            })
            entry["score"] += weight / (60 + rank)
            entry["methods"].append(method)
            entry["exact_match"] = entry["exact_match"] or exact_match

    ranked = sorted(combined.values(), key=lambda item: item["score"], reverse=True)[:n_results]
    max_score = ranked[0]["score"] if ranked else 1.0
    documents, metadatas, scores = [], [], []
    for item in ranked:
        payload = dict(item["point"].payload or {})
        documents.append(payload.pop("text", ""))
        payload.pop("branch_id", None)
        normalized_score = item["score"] / max_score
        payload.update({
            "retrieval_methods": sorted(set(item["methods"])),
            "retrieval_score": round(normalized_score, 4),
            "exact_match": item["exact_match"],
        })
        metadatas.append(payload)
        scores.append(normalized_score)

    return {"documents": [documents], "metadatas": [metadatas], "scores": [scores]}


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
    Dense semantic search plus BM25 lexical search, fused with weighted
    reciprocal-rank fusion. Graph expansion happens in the /ask context builder.
    """
    branch_filter = Filter(must=[FieldCondition(key="branch_id", match=MatchValue(value=branch_id))])
    dense_query = create_embedding(query)
    dense_results = client.query_points(
        collection_name=COLLECTION,
        query=dense_query,
        using=DENSE_VECTOR_NAME,
        query_filter=branch_filter,
        limit=max(n_results, HYBRID_DENSE_CANDIDATES),
    )
    lexical_results = _lexical_rank(
        query,
        branch_id,
        limit=max(n_results, HYBRID_LEXICAL_CANDIDATES),
    )
    return _hybrid_shape(dense_results.points, lexical_results, n_results)
