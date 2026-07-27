import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


def get_session():
    return SessionLocal()


def init_db():
    """Create all tables that don't exist yet. Safe to call on every startup."""
    from app.storage import models  # noqa: F401 (registers models on Base.metadata)

    Base.metadata.create_all(bind=engine)

    # create_all() only adds missing tables, not missing columns on existing
    # ones — there's no Alembic in this project, so new report columns get
    # added here instead. IF NOT EXISTS makes it safe to run on every startup.
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS architecture_report JSONB"))
        conn.execute(text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS call_graph_report JSONB"))
