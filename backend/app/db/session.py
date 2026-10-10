from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()
_engine = None
_SessionLocal = None


def get_engine():
    """Create the SQLAlchemy engine only when DATABASE_URL is configured."""
    global _engine, _SessionLocal
    if not settings.database_url:
        raise RuntimeError(
            "DATABASE_URL is not configured. Set it in backend/.env before using database routes."
        )
    if _engine is None:
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_recycle=300,
        )
        _SessionLocal = sessionmaker(
            bind=_engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
    return _engine


def get_db() -> Generator[Session, None, None]:
    get_engine()
    assert _SessionLocal is not None
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()
