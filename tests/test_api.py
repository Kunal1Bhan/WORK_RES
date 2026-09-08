import pytest
from fastapi.testclient import TestClient

from app.db import init_db
from app.main import INJECT, app


@pytest.fixture()
def client():
    init_db()
    INJECT["latency_ms"] = 0
    INJECT["error_rate"] = 0.0
    with TestClient(app) as c:
        yield c


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_order_flow(client):
    r = client.post("/api/orders", json={"item": "book"})
    assert r.status_code == 200
    oid = r.json()["id"]
    got = client.get(f"/api/orders/{oid}")
    assert got.status_code == 200
    assert got.json()["item"] == "book"


def test_order_not_found(client):
    assert client.get("/api/orders/999999").status_code == 404


def test_ready(client):
    body = client.get("/ready").json()
    assert body["db"] == "up"
    assert "queue_depth" in body


def test_chaos_validation(client):
    assert client.post("/chaos", json={"error_rate": 2.0}).status_code == 422
    assert client.post("/chaos", json={"latency_ms": -1}).status_code == 422
    assert client.post("/chaos", json={"error_rate": 1.0}).status_code == 200
    # full error rate => creation fails (injected)
    assert client.post("/api/orders", json={"item": "x"}).status_code == 500
    client.post("/chaos", json={"error_rate": 0.0})


def test_worker_processes_order(client):
    from app.worker import process_one

    r = client.post("/api/orders", json={"item": "widget"})
    oid = r.json()["id"]
    assert process_one(f'{{"order_id": {oid}, "item": "widget"}}') == "ok"
    got = client.get(f"/api/orders/{oid}")
    assert got.status_code == 200
