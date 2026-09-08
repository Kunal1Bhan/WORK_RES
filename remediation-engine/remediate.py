#!/usr/bin/env python3
"""Policy remediation engine (M5): evaluate policies.yaml against live signals,
act with cooldown safeguards, keep an audit log.

Signals: /ready (db, queue_depth), Prometheus (error_rate_2m) when PROM_URL set.
Actions: clear_chaos (POST /chaos reset), page (log only).

Usage:
  python remediation-engine/remediate.py [--api URL] [--prom URL] [--dry-run] [--once]
"""
import argparse
import json
import os
import time
import urllib.request

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(HERE, ".policy-state.json")
AUDIT_FILE = os.path.join(HERE, "audit.log")


def load_policies():
    with open(os.path.join(HERE, "policies.yaml")) as f:
        return yaml.safe_load(f)["policies"]


def _get(url):
    with urllib.request.urlopen(url, timeout=5) as r:
        return r.read().decode()


def fetch_signals(api, prom):
    signals = {"error_rate_2m": 0.0, "queue_depth": 0, "db_up": 1}
    try:
        ready = json.loads(_get(api + "/ready"))
        signals["queue_depth"] = ready.get("queue_depth", 0)
        signals["db_up"] = 1 if ready.get("db") == "up" else 0
    except Exception as e:
        signals["db_up"] = 0
        signals["fetch_error"] = str(e)
    if prom:
        try:
            q = ("query?query=sum(rate(lab_http_requests_total{status=~\"5..\"}[2m]))"
                 "/sum(rate(lab_http_requests_total[2m]))")
            data = json.loads(_get(prom + "/api/v1/" + q))
            res = data.get("data", {}).get("result", [])
            if res:
                signals["error_rate_2m"] = float(res[0]["value"][1])
        except Exception as e:
            signals["prom_error"] = str(e)
    return signals


def match(cond, signals):
    v = signals.get(cond["metric"], 0)
    op, t = cond["op"], cond["value"]
    return {">": v > t, ">=": v >= t, "<": v < t,
            "==": v == t, "!=": v != t}[op]


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def audit(entry):
    entry["ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(AUDIT_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(json.dumps(entry))


def do_clear_chaos(api, dry_run):
    if dry_run:
        return "dry-run: would POST /chaos reset"
    req = urllib.request.Request(api + "/chaos",
                                 data=json.dumps({"latency_ms": 0, "error_rate": 0.0}).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=5) as r:
        return "cleared_chaos: " + r.read().decode()


def run_once(api, prom, dry_run):
    policies = load_policies()
    signals = fetch_signals(api, prom)
    state = load_state()
    now = time.time()
    acted = []
    for pol in policies:
        st = state.get(pol["name"], {"attempts": 0, "last": 0})
        if not match(pol["when"], signals):
            continue
        if now - st.get("last", 0) < pol["cooldown_seconds"]:
            audit({"policy": pol["name"], "result": "skipped_cooldown", "signals": signals})
            continue
        if st.get("attempts", 0) >= pol["max_attempts"]:
            audit({"policy": pol["name"], "result": "skipped_max_attempts", "signals": signals})
            continue
        action = pol["action"]
        if action == "clear_chaos":
            try:
                result = do_clear_chaos(api, dry_run)
            except Exception as e:
                result = f"action_failed: {e}"
        elif action == "page":
            result = "paged (log only)"
        else:
            result = f"unknown_action: {action}"
        st["attempts"] = st.get("attempts", 0) + (0 if dry_run else 1)
        st["last"] = now
        state[pol["name"]] = st
        acted.append(pol["name"])
        audit({"policy": pol["name"], "action": action, "result": result, "signals": signals})
    save_state(state)
    if not acted:
        audit({"result": "no_policy_matched", "signals": signals})
    return acted


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--api", default="http://localhost:8000")
    p.add_argument("--prom", default="")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--once", action="store_true")
    p.add_argument("--loop-seconds", type=int, default=30)
    a = p.parse_args(argv)
    if a.once or a.dry_run:
        run_once(a.api, a.prom, a.dry_run)
        return
    while True:
        try:
            run_once(a.api, a.prom, False)
        except Exception as e:
            audit({"result": f"loop_error: {e}"})
        time.sleep(a.loop_seconds)


if __name__ == "__main__":
    main()
