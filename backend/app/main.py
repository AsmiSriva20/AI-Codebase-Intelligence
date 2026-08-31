from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()  # Loads variables from .env into os.environ

from app import state
from app.config import CORS_ALLOWED_ORIGINS
from app.storage.db import engine, init_db
from app.storage.vectordb import client as qdrant_client
from app.routers import repository, search, code_health, architecture, git_intel, realtime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.api_route("/health", methods=["GET", "HEAD"], tags=["health"])
def health_check():
    """Lightweight liveness check for Render and external uptime monitors."""
    return {"status": "ok"}


@app.api_route("/health/postgres", methods=["GET", "HEAD"], tags=["health"])
def postgres_health_check():
    """Confirm that the API can connect to PostgreSQL and execute a query."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok", "service": "postgres"}
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "service": "postgres"},
        )


@app.api_route("/health/qdrant", methods=["GET", "HEAD"], tags=["health"])
def qdrant_health_check():
    """Confirm that the API can authenticate with and query Qdrant."""
    try:
        qdrant_client.get_collections()
        return {"status": "ok", "service": "qdrant"}
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "service": "qdrant"},
        )


@app.on_event("startup")
def _on_startup():
    init_db()
    state.rehydrate_from_db()


app.include_router(repository.router)
app.include_router(search.router)
app.include_router(code_health.router)
app.include_router(architecture.router)
app.include_router(git_intel.router)
app.include_router(realtime.router)
