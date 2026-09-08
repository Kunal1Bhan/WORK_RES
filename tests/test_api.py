import pytest
from fastapi.testclient import TestClient

import app.main as mainmod
from app.db import init_db
from app.main import INJECT, app


@pytest.fixture()
def client():
    init_db()
    INJECT["latency_ms"] = 0
    INJECT["error_rate"] = 0.0
    mainmod._buckets.clear()
    mainmod.settings.API_KEY = ""
    mainmod.settings.RATE_LIMIT_RPS = 0
    mainmod.settings.CHAOS_ENABLED = True
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_live(client):
    assert client.get("/live").json() == {"status": "ok"}


def test_order_flow(client):
    r = client.post("/api/orders", json={"item": "book"})
    assert r.status_code == 201
    assert r.headers["Location"].startswith("/api/orders/")
    oid = r.json()["id"]
    got = client.get(f"/api/orders/{oid}")
    assert got.status_code == 200
    assert got.json()["item"] == "book"


def test_order_not_found_envelope(client):
    r = client.get("/api/orders/999999")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


def test_order_validation(client):
    assert client.post("/api/orders", json={"item": ""}).status_code == 422
    assert client.post("/api/orders", json={"item": "x" * 201}).status_code == 422
    assert client.post("/api/orders", json={}).status_code == 422


def test_list_pagination(client):
    for i in range(3):
        assert client.post("/api/orders", json={"item": f"p{i}"}).status_code == 201
    page = client.get("/api/orders?limit=2&offset=0").json()
    assert page["limit"] == 2 and len(page["items"]) == 2
    assert page["total"] >= 3
    assert client.get("/api/orders?limit=100000").json()["limit"] <= 100


def test_security_headers(client):
    r = client.get("/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert "X-Request-ID" in r.headers


def test_ready(client):
    body = client.get("/ready").json()
    assert body["db"] == "up"
    assert "queue_depth" in body


def test_chaos_validation(client):
    assert client.post("/chaos", json={"error_rate": 2.0}).status_code == 422
    assert client.post("/chaos", json={"latency_ms": -1}).status_code == 422
    assert client.post("/chaos", json={"latency_ms": "soon"}).status_code == 422
    assert client.post("/chaos", json={"error_rate": 1.0}).status_code == 200
    r = client.post("/api/orders", json={"item": "x"})
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "injected_failure"
    client.post("/chaos", json={"error_rate": 0.0})


def test_chaos_disabled(client):
    mainmod.settings.CHAOS_ENABLED = False
    r = client.post("/chaos", json={"error_rate": 0.5})
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "forbidden"


def test_api_key_gate(client):
    mainmod.settings.API_KEY = "secret-123"
    assert client.post("/api/orders", json={"item": "x"}).status_code == 401
    assert client.post("/chaos", json={}).status_code == 401
    assert client.get("/health").status_code == 200  # public stays open
    h = {"X-API-Key": "secret-123"}
    assert client.post("/api/orders", json={"item": "x"}, headers=h).status_code == 201
    bad = client.get("/api/orders/1", headers={"X-API-Key": "wrong"})
    assert bad.status_code == 401


def test_rate_limit(client):
    mainmod.settings.RATE_LIMIT_RPS = 2
    mainmod.settings.RATE_LIMIT_BURST = 2
    codes = [client.get("/health").status_code for _ in range(6)]
    assert 429 in codes


def test_worker_processes_order(client):
    from app.worker import process_one

    r = client.post("/api/orders", json={"item": "widget"})
    oid = r.json()["id"]
    assert process_one(f'{{"order_id": {oid}, "item": "widget"}}') == "ok"
    got = client.get(f"/api/orders/{oid}")
    assert got.status_code == 200
