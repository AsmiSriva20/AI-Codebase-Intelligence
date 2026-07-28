"""Centralized, environment-overridable configuration.

Every value here used to be a literal hardcoded directly in whatever module
needed it — several of them (the repo checkout path, the max-file-size
threshold, the binary-extension skip list) were duplicated with slight drift
across two or three files. Collecting them here gives one source of truth and
one place to tune per-environment via env vars, without touching code.

Required secrets (QDRANT_URL, QDRANT_API_KEY, GROQ_API_KEY, DATABASE_URL) are
intentionally NOT centralized here — they're read directly via os.environ[...]
in the module that needs them (storage/vectordb.py, llm/client.py,
storage/db.py) so that importing this module never fails just because an
unrelated service's credentials aren't configured yet.
"""
import os
import tempfile


def _env_int(name, default):
    return int(os.environ.get(name, default))


def _env_float(name, default):
    return float(os.environ.get(name, default))


def _env_list(name, default):
    raw = os.environ.get(name)
    if raw is None:
        return list(default)
    return [item.strip() for item in raw.split(",") if item.strip()]


# --- Repository checkout ---
# Ephemeral scratch space for whatever repo is currently cloned. Defaults to
# the OS temp dir rather than a path relative to the app's working directory:
# most cloud hosts (Render, Railway, Heroku, Fly, containers running as a
# non-root user) run the app from a read-only or otherwise non-writable
# project directory and only guarantee a writable temp dir. Override REPOS_DIR
# if you mount a persistent volume instead.
REPOS_DIR = os.environ.get("REPOS_DIR", os.path.join(tempfile.gettempdir(), "aci-repos"))
REPO_PATH = os.path.join(REPOS_DIR, "repository")

# --- File scanning / indexing limits ---
MAX_INDEXABLE_FILE_SIZE = _env_int("MAX_INDEXABLE_FILE_SIZE", 400_000)
LARGE_FILE_LINES = _env_int("LARGE_FILE_LINES", 600)

SCAN_IGNORE_DIRS = set(_env_list("SCAN_IGNORE_DIRS", [
    ".git", "node_modules", "dist", "build", "venv", ".venv", "__pycache__",
    "target", "vendor", ".next", ".egg-info",
]))

BINARY_SKIP_EXTENSIONS = set(_env_list("BINARY_SKIP_EXTENSIONS", [
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp", ".bmp",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".pdf", ".zip", ".gz", ".tar", ".7z",
    ".lock", ".map", ".min.js", ".pyc", ".so", ".dll", ".exe", ".bin",
]))

# --- Qdrant (tunables only — QDRANT_URL/QDRANT_API_KEY stay in vectordb.py) ---
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "repository")
QDRANT_TIMEOUT_SECONDS = _env_int("QDRANT_TIMEOUT_SECONDS", 60)
QDRANT_VECTOR_SIZE = _env_int("QDRANT_VECTOR_SIZE", 384)  # must match EMBEDDING_MODEL_NAME's output dimension
QDRANT_UPSERT_BATCH_SIZE = _env_int("QDRANT_UPSERT_BATCH_SIZE", 25)
QDRANT_UPSERT_MAX_RETRIES = _env_int("QDRANT_UPSERT_MAX_RETRIES", 3)
DEFAULT_BRANCH_ID = os.environ.get("DEFAULT_BRANCH_ID", "default")

# --- Embeddings ---
# Empty/unset means "let fastembed pick its own default" (currently BAAI/bge-small-en-v1.5).
EMBEDDING_MODEL_NAME = os.environ.get("EMBEDDING_MODEL_NAME") or None
SPARSE_EMBEDDING_MODEL_NAME = os.environ.get("SPARSE_EMBEDDING_MODEL_NAME", "Qdrant/bm25")
EMBEDDING_BATCH_SIZE = _env_int("EMBEDDING_BATCH_SIZE", 32)

# --- Chunking (controls embedding cost/granularity per file) ---
CHUNK_WINDOW_LINES = _env_int("CHUNK_WINDOW_LINES", 40)
CHUNK_MAX_TEXT_CHUNKS_PER_FILE = _env_int("CHUNK_MAX_TEXT_CHUNKS_PER_FILE", 12)
CHUNK_MAX_CHARS = _env_int("CHUNK_MAX_CHARS", 3000)

# --- Search defaults ---
SEARCH_DEFAULT_N_RESULTS = _env_int("SEARCH_DEFAULT_N_RESULTS", 5)
SEARCH_DENSE_ONLY_N_RESULTS = _env_int("SEARCH_DENSE_ONLY_N_RESULTS", 15)

# --- LLM (Groq) ---
LLM_MODEL_NAME = os.environ.get("LLM_MODEL_NAME", "llama-3.3-70b-versatile")
LLM_TEMPERATURE = _env_float("LLM_TEMPERATURE", 0.2)
LLM_EXPLAIN_FILE_MAX_CHARS = _env_int("LLM_EXPLAIN_FILE_MAX_CHARS", 8000)
LLM_SUMMARY_MAX_FILES = _env_int("LLM_SUMMARY_MAX_FILES", 20)
LLM_SUMMARY_MAX_ITEMS_PER_FILE = _env_int("LLM_SUMMARY_MAX_ITEMS_PER_FILE", 3)

# --- Git history / hotspots ---
GIT_HISTORY_MAX_COMMITS = _env_int("GIT_HISTORY_MAX_COMMITS", 50)
HOTSPOTS_DEFAULT_SINCE_DAYS = _env_int("HOTSPOTS_DEFAULT_SINCE_DAYS", 90)
HOTSPOTS_TOP_N = _env_int("HOTSPOTS_TOP_N", 20)

# --- Dependency vulnerability scan (OSV.dev) ---
OSV_ENDPOINT = os.environ.get("OSV_ENDPOINT", "https://api.osv.dev/v1/querybatch")
OSV_REQUEST_TIMEOUT_SECONDS = _env_int("OSV_REQUEST_TIMEOUT_SECONDS", 6)

# --- CORS ---
CORS_ALLOWED_ORIGINS = _env_list("CORS_ALLOWED_ORIGINS", ["http://localhost:5173"])
