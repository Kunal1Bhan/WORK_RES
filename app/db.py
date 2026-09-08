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
    product_id = Column(Integer, nullable=True)
    qty = Column(Integer, default=1)
    total_cents = Column(Integer, default=0)
    promo = Column(String(20), nullable=True)

    __table_args__ = (
        Index("ix_orders_status", "status"),
        Index("ix_orders_created", "created_at"),
    )


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True)
    price_cents = Column(Integer, nullable=False, default=0)
    stock = Column(Integer, nullable=False, default=0)


class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    ts = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    kind = Column(String(50), nullable=False)
    detail = Column(String(500), nullable=False, default="")


# Promo codes (real-shop feature): code -> discount fraction.
PROMOS = {"SAVE10": 0.10, "HALF": 0.50}


def log_event(session, kind, detail=""):
    session.add(Event(kind=kind, detail=detail[:500]))
    # prune: keep the feed bounded
    try:
        n = session.query(Event).count()
        if n > 500:
            oldest = session.query(Event).order_by(Event.id).limit(n - 500).all()
            for e in oldest:
                session.delete(e)
    except Exception:
        pass


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
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False,
                                     autocommit=False, expire_on_commit=False)
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
    # Lightweight migrations (idempotent on PG + SQLite).
    from sqlalchemy import text as _text
    with eng.begin() as conn:
        conn.execute(_text(
            "CREATE INDEX IF NOT EXISTS ix_orders_status ON orders (status)"))
        conn.execute(_text(
            "CREATE INDEX IF NOT EXISTS ix_orders_created ON orders (created_at)"))
    # One transaction per ALTER: on Postgres a duplicate-column error aborts
    # its transaction, so they must not share one.
    for ddl in (
        "ALTER TABLE orders ADD COLUMN product_id INTEGER",
        "ALTER TABLE orders ADD COLUMN qty INTEGER DEFAULT 1",
        "ALTER TABLE orders ADD COLUMN total_cents INTEGER DEFAULT 0",
        "ALTER TABLE orders ADD COLUMN promo VARCHAR(20)",
    ):
        try:
            with eng.begin() as conn:
                conn.execute(_text(ddl))
        except Exception:
            pass  # column already exists


def get_session():
    get_engine()
    return _SessionLocal()
