import json
import remediate
from remediate import match, run_once


def test_match_ops():
    assert match({"metric": "a", "op": ">", "value": 1}, {"a": 2})
    assert not match({"metric": "a", "op": ">", "value": 1}, {"a": 1})
    assert match({"metric": "a", "op": "==", "value": 0}, {"a": 0})


def test_run_once_clears(monkeypatch, tmp_path):
    monkeypatch.setattr(remediate, "STATE_FILE", str(tmp_path / "s.json"))
    monkeypatch.setattr(remediate, "AUDIT_FILE", str(tmp_path / "a.log"))
    monkeypatch.setattr(remediate, "fetch_signals",
                        lambda api, prom: {"error_rate_2m": 0.5, "queue_depth": 0, "db_up": 1})
    calls = []
    monkeypatch.setattr(remediate, "do_clear_chaos",
                        lambda api, dry: calls.append((api, dry)) or "ok")
    acted = run_once("http://x", "", False)
    assert acted == ["clear-injected-errors"]
    assert len(calls) == 1
    # second run within cooldown -> skip
    acted2 = run_once("http://x", "", False)
    assert acted2 == []
    assert len(calls) == 1
    audit = open(tmp_path / "a.log").read().strip().split("\n")
    assert len(audit) == 3  # act, then skipped_cooldown + no_policy_matched
    assert json.loads(audit[0])["policy"] == "clear-injected-errors"
    assert json.loads(audit[1])["result"] == "skipped_cooldown"
    assert json.loads(audit[2])["result"] == "no_policy_matched"


def test_run_once_no_match(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(remediate, "STATE_FILE", str(tmp_path / "s.json"))
    monkeypatch.setattr(remediate, "AUDIT_FILE", str(tmp_path / "a.log"))
    monkeypatch.setattr(remediate, "fetch_signals",
                        lambda api, prom: {"error_rate_2m": 0.0, "queue_depth": 0, "db_up": 1})
    assert run_once("http://x", "", True) == []
    assert "no_policy_matched" in capsys.readouterr().out
