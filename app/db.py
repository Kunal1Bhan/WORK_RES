"""Shared DB layer: Postgres when DATABASE_URL is set, else local SQLite.

Engine is created lazily so tests can override DATABASE_URL via env
before the first connection is made.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Index, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings

Base = declarative_base()
_engine = None
_SessionLocal = None


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    item = Column(String(200), nullable=False)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_orders_status", "status"),
        Index("ix_orders_created", "created_at"),
    )


def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        url = settings.DATABASE_URL
        kwargs = {}
        if url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
        else:
            kwargs.update(pool_size=settings.POOL_SIZE,
                          max_overflow=settings.POOL_MAX_OVERFLOW,
                          pool_pre_ping=True)
        _engine = create_engine(url, **kwargs)
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    return _engine


def reset_engine():
    """For tests: drop the cached engine so a new DATABASE_URL takes effect."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


def init_db():
    eng = get_engine()
    Base.metadata.create_all(bind=eng)
    # Lightweight migration: create_all skips existing tables, so ensure
    # newer indexes exist explicitly (idempotent on PG + SQLite).
    from sqlalchemy import text as _text
    with eng.begin() as conn:
        conn.execute(_text(
            "CREATE INDEX IF NOT EXISTS ix_orders_status ON orders (status)"))
        conn.execute(_text(
            "CREATE INDEX IF NOT EXISTS ix_orders_created ON orders (created_at)"))


def get_session():
    get_engine()
    return _SessionLocal()
