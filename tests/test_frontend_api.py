"""Frontend API-integration matrix: every status a UI surface can meet."""
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


def test_unknown_route_json_envelope(client):
    r = client.get("/nope")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "http_404"
    assert r.headers["Content-Type"].startswith("application/json")


def test_method_not_allowed(client):
    r = client.delete("/api/orders/1")
    assert r.status_code == 405


def test_validation_envelope_shape(client):
    r = client.post("/api/orders", json={"item": ""})
    assert r.status_code == 422
    body = r.json()
    assert body["error"]["code"] == "validation_error"
    assert "message" in body["error"]


def test_malformed_json(client):
    r = client.post("/api/orders", content=b"{bad json",
                    headers={"Content-Type": "application/json"})
    assert r.status_code == 422


def test_chaos_500_envelope(client):
    client.post("/chaos", json={"error_rate": 1.0})
    r = client.post("/api/orders", json={"item": "x"})
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "injected_failure"
    client.post("/chaos", json={"error_rate": 0.0})


def test_list_empty_shape(client):
    import app.db as dbmod
    s = dbmod.get_session()
    try:
        s.query(dbmod.Order).delete()
        s.commit()
    finally:
        s.close()
    body = client.get("/api/orders").json()
    assert body == {"total": 0, "limit": 20, "offset": 0, "items": []}
