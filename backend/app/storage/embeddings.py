import os
import time

import requests

from app.config import (
    GEMINI_EMBEDDING_DIMENSION,
    GEMINI_EMBEDDING_MAX_RETRIES,
    GEMINI_EMBEDDING_MODEL,
    GEMINI_EMBEDDING_TIMEOUT_SECONDS,
)


def _document_text(text, title=None):
    return f"title: {title or 'none'} | text: {text}"


def _query_text(text):
    return f"task: code retrieval | query: {text}"


def _embed_texts(texts):
    """Call Gemini's synchronous batch endpoint; store no model files locally."""
    model_path = f"models/{GEMINI_EMBEDDING_MODEL}"
    url = f"https://generativelanguage.googleapis.com/v1beta/{model_path}:batchEmbedContents"
    payload = {
        "requests": [
            {
                "model": model_path,
                "content": {"parts": [{"text": text}]},
                "outputDimensionality": GEMINI_EMBEDDING_DIMENSION,
            }
            for text in texts
        ]
    }

    for attempt in range(1, GEMINI_EMBEDDING_MAX_RETRIES + 1):
        try:
            response = requests.post(
                url,
                headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]},
                json=payload,
                timeout=GEMINI_EMBEDDING_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            embeddings = [item["values"] for item in response.json()["embeddings"]]
            if len(embeddings) != len(texts):
                raise RuntimeError("Gemini returned a different number of embeddings than requested")
            return embeddings
        except (requests.RequestException, KeyError, RuntimeError):
            if attempt == GEMINI_EMBEDDING_MAX_RETRIES:
                raise
            time.sleep(2 * attempt)


def create_embedding(text):
    return _embed_texts([_query_text(text)])[0]


def embed_batch(batch):
    vectors = _embed_texts([
        _document_text(chunk["text"], chunk.get("metadata", {}).get("path"))
        for chunk in batch
    ])
    return [
        {"text": chunk["text"], "metadata": chunk["metadata"], "embedding": vector}
        for chunk, vector in zip(batch, vectors)
    ]
