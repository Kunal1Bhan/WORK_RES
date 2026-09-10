"""Scheduler + node-loss policy tests."""
import json
import schedule as schedmod
from schedule import due_jobs, run_once


def test_due_jobs():
    jobs = [{"file": "a.yaml", "every_seconds": 60}]
    assert due_jobs(jobs, {}, 1000) == jobs
    assert due_jobs(jobs, {"a.yaml": 990}, 1000) == []
    assert due_jobs(jobs, {"a.yaml": 990}, 1000, force=True) == jobs


def test_run_once_logs(monkeypatch, tmp_path):
    monkeypatch.setattr(schedmod, "STATE", str(tmp_path / "s.json"))
    monkeypatch.setattr(schedmod, "LOG", str(tmp_path / "r.jsonl"))
    monkeypatch.setattr(schedmod, "run_file", lambda path, api: True)
    sched = tmp_path / "sched.yaml"
    sched.write_text("jobs:\n  - {file: e.yaml, every_seconds: 3600}\n")
    ran = run_once(str(sched), "http://x", str(tmp_path))
    assert ran and ran[0]["passed"] is True
    assert json.loads(open(tmp_path / "r.jsonl").read())["job"] == "e.yaml"
    assert run_once(str(sched), "http://x", str(tmp_path)) == []  # cooldown


def test_node_loss_policy(monkeypatch):
    import remediate
    from remediate import match
    assert match({"metric": "node_loss_pct", "op": ">=", "value": 30},
                 {"node_loss_pct": 35})
    monkeypatch.setenv("NODE_LOSS_PCT", "35")
    sigs = remediate.fetch_signals("http://127.0.0.1:9", "")
    assert sigs["node_loss_pct"] == 35.0
