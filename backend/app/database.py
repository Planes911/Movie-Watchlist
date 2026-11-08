"""Database engine, session factory and the declarative base for SQLAlchemy 2.0."""

from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings

class Base(DeclarativeBase):
    """Shared declarative base class for all ORM models."""
    pass

def make_engine(url: str):
    """Create an engine tuned for SQLite (dev/tests) or PostgreSQL (production)."""
    kwargs: dict = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if url in ("sqlite://", "sqlite:///:memory:"):
            # In-memory SQLite is private to each connection; StaticPool makes every session share
            # one database (used by the test suite).
            kwargs["poolclass"] = StaticPool
    else:
        # Transparently drop dead connections (e.g. after a free-tier database or host went idle).
        kwargs["pool_pre_ping"] = True 
        # Supabase's pooler runs in transaction mode, which does not support prepared statements.
        if "pooler.supabase.com" in url:
            kwargs["connect_args"] = {"prepare_threshold": None}
        
    engine = create_engine(url, **kwargs)
        
    if url.startswith("sqlite"):
        # SQLite ignores foreign keys by default; enable them so it behaves like PostgreSQL.
        @event.listens_for(engine, "connect")
        def _enable_fk(dbapi_conn, _record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
            
    return engine

# Created once at import time and shared by the whole application.
engine = make_engine(get_settings().database_url)
# expire_on_commit=False keeps objects readable after commit (responses are built right after).
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

def get_db() -> Iterator[Session]:
    """FastAPI dependency: one database session per request, always closed afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        