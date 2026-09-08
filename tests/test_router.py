import router
from router import Router, pick


def test_pick_none_when_zero():
    assert pick([0.0, 0.0]) is None


def test_effective_weights():
    r = Router(["http://a", "http://b"], [3.0, 1.0])
    r.healthy = [True, False]
    assert r.effective_weights() == [3.0, 0.0]


def test_all_down_502():
    r = Router(["http://a"])
    r.healthy = [False]
    code, body = r.route("/health")
    assert code == 502
    assert "all regions down" in body["error"]


def test_refresh_marks_health(monkeypatch):
    monkeypatch.setattr(router, "check", lambda url, timeout=2: "good" in url)
    r = Router(["http://good", "http://bad"])
    assert r.refresh() == [True, False]
