"""Teams RBAC + plugin loader tests."""
import app.main as mainmod
from app.db import init_db
from app.main import app
from fastapi.testclient import TestClient


def _client():
    init_db()
    mainmod._buckets.clear()
    mainmod.settings.API_KEY = ""
    mainmod.settings.RATE_LIMIT_RPS = 0
    mainmod.settings.CHAOS_ENABLED = True
    return TestClient(app, raise_server_exceptions=False)


def test_member_cannot_chaos_but_can_order(tmp_path):
    teams = tmp_path / "teams.yaml"
    teams.write_text("teams:\n"
                     "  - {key: adm-1, team: a, role: admin}\n"
                     "  - {key: mem-1, team: b, role: member}\n")
    mainmod.settings.TEAMS_FILE = str(teams)
    try:
        with _client() as c:
            assert c.post("/api/orders", json={"item": "x"}).status_code == 401
            m = {"X-API-Key": "mem-1"}
            assert c.post("/api/orders", json={"item": "x"}, headers=m).status_code == 201
            assert c.post("/chaos", json={}, headers=m).status_code == 403
            a = {"X-API-Key": "adm-1"}
            assert c.post("/chaos", json={"error_rate": 0}, headers=a).status_code == 200
    finally:
        mainmod.settings.TEAMS_FILE = ""


def test_plugin_loader(tmp_path):
    import sys
    sys.path.insert(0, "plugins")
    from loader import load_plugins
    (tmp_path / "demo.py").write_text(
        "def register():\n"
        "    return {'name': 'demo', 'run': lambda api, p: (True, 'ok')}\n")
    (tmp_path / "broken.py").write_text("raise RuntimeError('boom')\n")
    plugins = load_plugins(str(tmp_path))
    assert callable(plugins["demo"])
    assert plugins["demo"]("http://x", {}) == (True, "ok")
    assert "broken.py" in plugins  # load errors reported, not raised


def test_sample_plugin_registered():
    import sys
    sys.path.insert(0, "plugins")
    from loader import load_plugins
    import os
    lab = os.path.dirname(os.path.dirname(os.path.abspath("plugins/loader.py")))
    _ = lab
    plugins = load_plugins("plugins")
    assert "latency_spike" in plugins and callable(plugins["latency_spike"])
