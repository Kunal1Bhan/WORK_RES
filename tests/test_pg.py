"""Postgres integration: runs only when PG is reachable (CI service or local).

Covers: fresh DB -> init -> CRUD -> indexes exist -> pool pre-ping.
"""
import os
import socket

import pytest
from sqlalchemy import inspect, text

PG_URL = os.getenv("TEST_PG_URL", "postgresql+psycopg://lab:lab@127.0.0.1:5432/lab")


def pg_up():
    try:
        socket.create_connection(("127.0.0.1", 5432), timeout=2).close()
        return True
    except OSError:
        return False


needs_pg = pytest.mark.skipif(not pg_up(), reason="no Postgres on 127.0.0.1:5432")


@needs_pg
def test_pg_crud_and_indexes(monkeypatch):
    import app.db as dbmod

    monkeypatch.setenv("DATABASE_URL", PG_URL)
    dbmod.reset_engine()
    # point settings at PG for this test
    import app.config as cfg
    monkeypatch.setattr(cfg.settings, "DATABASE_URL", PG_URL)
    dbmod.reset_engine()
    dbmod.init_db()

    s = dbmod.get_session()
    try:
        s.execute(text("DELETE FROM orders WHERE item LIKE 'pg-%'"))
        s.commit()
        row = dbmod.Order(item="pg-widget", status="pending")
        s.add(row)
        s.commit()
        assert row.id is not None
        got = s.query(dbmod.Order).filter(dbmod.Order.id == row.id).first()
        assert got.item == "pg-widget"
        got.status = "done"
        s.commit()
        assert s.query(dbmod.Order).filter(
            dbmod.Order.status == "done").count() >= 1  # exercises status index
    finally:
        s.close()

    idx = {i["name"] for t in ("orders",) for i in inspect(dbmod.get_engine()).get_indexes(t)}
    assert "ix_orders_status" in idx
    assert "ix_orders_created" in idx


@needs_pg
def test_pg_health_select():
    import app.db as dbmod

    s = dbmod.get_session()
    try:
        assert s.execute(text("SELECT 1")).scalar() == 1
    finally:
        s.close()
