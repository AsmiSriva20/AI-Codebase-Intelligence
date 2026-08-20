import os
import time

import requests

from app.config import (
    OPENAI_EMBEDDING_DIMENSION,
    OPENAI_EMBEDDING_MAX_RETRIES,
    OPENAI_EMBEDDING_MODEL,
    OPENAI_EMBEDDING_RETRY_BASE_SECONDS,
    OPENAI_EMBEDDING_TIMEOUT_SECONDS,
)


def _api_key():
    # Accept the user's existing spelling, but prefer OpenAI's standard name.
    key = os.environ.get("OPENAI_API_KEY") or os.environ.get("OpenAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    return key


def _document_text(text, title=None):
    return f"File: {title}\n{text}" if title else text


def _retry_delay(response, attempt):
    if response is not None:
        retry_after_ms = response.headers.get("retry-after-ms")
        if retry_after_ms:
            try:
                return max(1, int(float(retry_after_ms) / 1000))
            except ValueError:
                pass
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return max(1, int(float(retry_after)))
            except ValueError:
                pass
    return min(OPENAI_EMBEDDING_RETRY_BASE_SECONDS * (2 ** (attempt - 1)), 60)


def _embed_texts(texts):
    """Create one OpenAI embedding per input without storing model files locally."""
    payload = {
        "model": OPENAI_EMBEDDING_MODEL,
        "input": texts,
        "dimensions": OPENAI_EMBEDDING_DIMENSION,
        "encoding_format": "float",
    }

    for attempt in range(1, OPENAI_EMBEDDING_MAX_RETRIES + 1):
        try:
            response = requests.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {_api_key()}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=OPENAI_EMBEDDING_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            data = sorted(response.json()["data"], key=lambda item: item["index"])
            embeddings = [item["embedding"] for item in data]
            if len(embeddings) != len(texts):
                raise RuntimeError("OpenAI returned a different number of embeddings than requested")
            if any(len(vector) != OPENAI_EMBEDDING_DIMENSION for vector in embeddings):
                raise RuntimeError("OpenAI returned an unexpected embedding dimension")
            return embeddings
        except (requests.RequestException, KeyError, RuntimeError) as error:
            if attempt == OPENAI_EMBEDDING_MAX_RETRIES:
                raise
            delay = _retry_delay(getattr(error, "response", None), attempt)
            print(f"OpenAI embedding request failed; retrying in {delay}s (attempt {attempt})")
            time.sleep(delay)


def create_embedding(text):
    return _embed_texts([text])[0]


def embed_batch(batch):
    vectors = _embed_texts([
        _document_text(chunk["text"], chunk.get("metadata", {}).get("path"))
        for chunk in batch
    ])
    return [
        {"text": chunk["text"], "metadata": chunk["metadata"], "embedding": vector}
        for chunk, vector in zip(batch, vectors)
    ]
