"""React /app serving (fallback + live build)."""
import app.main as mainmod
from app.db import init_db
from app.main import app
from fastapi.testclient import TestClient


def _client():
    init_db()
    return TestClient(app, raise_server_exceptions=False)


def test_app_serves_built_dashboard():
    import os
    dist = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath("app/main.py"))), "web", "dist", "index.html")
    with _client() as c:
        r = c.get("/app")
        if os.path.exists(dist):
            assert r.status_code == 200
            assert "WORK_RES" in r.text
        else:
            assert r.status_code == 404
            assert r.json()["error"]["code"] == "not_found"


def test_app_fallback_and_traversal(monkeypatch):
    monkeypatch.setattr(mainmod, "_web_dist", lambda: None)
    with _client() as c:
        assert c.get("/app").status_code == 404
        assert c.get("/app/../secret").status_code in (404, 307)


def test_app_asset_traversal_blocked():
    with _client() as c:
        r = c.get("/app/assets/../../app/main.py")
        assert r.status_code in (404, 307)
