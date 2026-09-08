"""Shared DB layer: Postgres when DATABASE_URL is set, else local SQLite.

Engine is created lazily so tests can override DATABASE_URL via env
before the first connection is made.
"""
import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()
_engine = None
_SessionLocal = None


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    item = Column(String, nullable=False)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        url = os.getenv("DATABASE_URL", "sqlite:///./lab.db")
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, connect_args=connect_args)
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
    Base.metadata.create_all(bind=get_engine())


def get_session():
    get_engine()
    return _SessionLocal()
