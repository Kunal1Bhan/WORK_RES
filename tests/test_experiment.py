"""Experiment runner tests (monkeypatched transport, no server needed)."""
import experiment
from experiment import run_file, run_step


def test_unknown_action():
    ok, detail = run_step("http://x", {"action": "nuke"})
    assert not ok and "unknown action" in detail


def test_run_file_pass_and_report(monkeypatch, tmp_path):
    def fake(api, method, path, body=None):
        if path == "/chaos":
            return 200, {"inject": {}}
        if path == "/api/orders":
            return 201, {"id": 1}
        if path == "/api/situation":
            return 200, {"checks": [{"name": "availability", "verdict": "PASS"}]}
        raise AssertionError(path)

    monkeypatch.setattr(experiment, "api", fake)
    f = tmp_path / "e.yaml"
    f.write_text("name: t\nsteps:\n"
                 "  - {action: chaos, error_rate: 0.0}\n"
                 "  - {action: order, expect: 201}\n"
                 "  - {action: assert, check: availability, verdict: PASS}\n")
    assert run_file(str(f), "http://x") is True
    import json
    report = json.loads(open(str(f).replace(".yaml", ".report.json")).read())
    assert report["passed"] and len(report["results"]) == 3


def test_run_file_fail_stops(monkeypatch, tmp_path):
    def fake(api, method, path, body=None):
        if path == "/chaos":
            return 200, {}
        if path == "/api/situation":
            return 200, {"checks": [{"name": "availability", "verdict": "PASS"}]}
        raise AssertionError(path)

    monkeypatch.setattr(experiment, "api", fake)
    f = tmp_path / "e.yaml"
    f.write_text("name: t\nsteps:\n"
                 "  - {action: assert, check: availability, verdict: FAIL}\n"
                 "  - {action: assert, check: availability, verdict: PASS}\n")
    assert run_file(str(f), "http://x") is False
