"""Situation report: live deduction vs SLOs."""
from fastapi.testclient import TestClient

import app.main as mainmod
from app.db import init_db
from app.main import INJECT, app


def _client():
    init_db()
    INJECT["latency_ms"] = 0
    INJECT["error_rate"] = 0.0
    mainmod._buckets.clear()
    mainmod.settings.API_KEY = ""
    mainmod.settings.RATE_LIMIT_RPS = 0
    mainmod.settings.CHAOS_ENABLED = True
    return TestClient(app, raise_server_exceptions=False)


def test_situation_nominal():
    with _client() as c:
        c.get("/health")
        body = c.get("/api/situation").json()
        assert body["traffic"]["requests"] >= 1
        assert body["dependencies"]["db"] == "up"
        assert body["checks"], "must contain SLO checks"
        assert body["summary"]
        names = {k["name"] for k in body["checks"]}
        assert {"availability", "latency_p95", "queue_depth", "database",
                "chaos", "stock"} <= names


def test_situation_flags_chaos():
    with _client() as c:
        c.post("/chaos", json={"error_rate": 0.5})
        body = c.get("/api/situation").json()
        chaos = next(k for k in body["checks"] if k["name"] == "chaos")
        assert chaos["verdict"] == "WARN"
        assert any("injection ACTIVE" in r for r in body["recommendations"])
        assert "ATTENTION" in body["summary"] or "warning" in body["summary"]
        c.post("/chaos", json={"error_rate": 0.0})


def test_situation_fails_on_errors():
    with _client() as c:
        c.post("/chaos", json={"error_rate": 1.0})
        for _ in range(5):
            assert c.post("/api/orders", json={"item": "x"}).status_code == 500
        body = c.get("/api/situation").json()
        avail = next(k for k in body["checks"] if k["name"] == "availability")
        assert avail["verdict"] == "FAIL"
        assert "ATTENTION" in body["summary"]
        c.post("/chaos", json={"error_rate": 0.0})
