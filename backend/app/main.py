from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()  # Loads variables from .env into os.environ

from app import state
from app.config import CORS_ALLOWED_ORIGINS
from app.storage.db import init_db
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
