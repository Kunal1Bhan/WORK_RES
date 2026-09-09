"""Block-game scores API."""
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


def test_scores_flow():
    with _client() as c:
        assert c.get("/game").status_code == 200
        assert "text/html" in c.get("/game").headers["content-type"]
        assert c.post("/api/scores",
                      json={"name": "tester", "score": 500, "lines": 5, "level": 2}
                      ).status_code == 201
        assert c.post("/api/scores",
                      json={"name": "pro", "score": 1500, "lines": 12, "level": 3}
                      ).status_code == 201
        top = c.get("/api/scores?limit=5").json()["items"]
        assert top[0]["name"] == "pro" and top[0]["score"] == 1500
        assert c.get("/api/scores?limit=1").json()["items"].__len__() <= 1


def test_scores_validation():
    with _client() as c:
        assert c.post("/api/scores",
                      json={"name": "x", "score": -1, "lines": 0, "level": 1}
                      ).status_code == 422
        assert c.post("/api/scores",
                      json={"name": "x", "score": 10**9, "lines": 0, "level": 1}
                      ).status_code == 422
        long_name = c.post("/api/scores",
                           json={"name": "z", "score": 10, "lines": 0, "level": 1})
        assert long_name.status_code == 201
