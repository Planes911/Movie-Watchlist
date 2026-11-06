from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings

class Base(DeclarativeBase):
    pass

def make_engine(url: str):
    kwargs: dict = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if url in ("sqlite://", "sqlite:///:memory:"):
            kwargs["poolclass"] = StaticPool
    else:
        kwargs["pool_pre_ping"] = True 
        if "pooler.supabase.com" in url:
            kwargs["connect_args"] = {"prepare_threshold": None}
        
    engine = create_engine(url, **kwargs)
        
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _enable_fk(dbapi_conn, _record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
            
    return engine

engine = make_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

def get_db() -> Iterator[Session]:
    """Dependency FastAPI: satu session per request, selalu ditutup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()