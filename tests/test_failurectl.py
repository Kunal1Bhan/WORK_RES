"""Regression tests for failurectl arg parsing (no server needed)."""
import failurectl
from failurectl import main


def test_api_flag_before_subcommand(monkeypatch):
    seen = {}
    monkeypatch.setattr(failurectl, "_post", lambda api, body: seen.update(api=api, body=body))
    main(["--api", "http://example:1", "error", "--rate", "0.2"])
    assert seen == {"api": "http://example:1", "body": {"error_rate": 0.2}}


def test_api_flag_after_subcommand(monkeypatch):
    seen = {}
    monkeypatch.setattr(failurectl, "_post", lambda api, body: seen.update(api=api, body=body))
    main(["error", "--rate", "0.2", "--api", "http://example:2"])
    assert seen == {"api": "http://example:2", "body": {"error_rate": 0.2}}


def test_api_default(monkeypatch):
    seen = {}
    monkeypatch.setattr(failurectl, "_post", lambda api, body: seen.update(api=api, body=body))
    main(["clear"])
    assert seen["api"] == "http://localhost:8000"


def test_cpu_no_server_needed(capsys):
    main(["cpu", "--seconds", "1"])
    assert "event=cpu_burn" in capsys.readouterr().out
