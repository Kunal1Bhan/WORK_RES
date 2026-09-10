#!/usr/bin/env python3
"""experiment.py — custom chaos experiment builder/runner (FR2).
An experiment is YAML: named steps of chaos/wait/order/assert.
Asserts evaluate live state via /api/situation (no log plumbing needed).

Usage: python failure-engine/experiment.py experiments/error-burn.yaml [--api URL]
Exit code: 0 all asserts pass, 1 otherwise. Writes JSON report next to the file.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

import yaml


def api(api_base, method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(api_base + path, data=data,
                                 headers={"Content-Type": "application/json"},
                                 method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or "{}")
        except Exception:
            return e.code, {}
    except urllib.error.URLError as e:
        raise RuntimeError(f"API unreachable at {api_base}: {e}")


def run_step(api_base, step):
    kind = step.get("action")
    if kind == "chaos":
        code, body = api(api_base, "POST", "/chaos",
                         {"latency_ms": step.get("latency_ms", 0),
                          "error_rate": step.get("error_rate", 0.0)})
        return code == 200, f"chaos -> {code} {body}"
    if kind == "wait":
        time.sleep(float(step.get("seconds", 1)))
        return True, f"waited {step.get('seconds', 1)}s"
    if kind == "order":
        code, body = api(api_base, "POST", "/api/orders",
                         {"item": step.get("item", "exp-book")})
        ok = code == step.get("expect", 201)
        return ok, f"order -> {code} (expect {step.get('expect', 201)})"
    if kind == "plugin":
        import os as _os
        import sys as _sys
        _sys.path.insert(0, _os.path.join(_os.path.dirname(
            _os.path.dirname(_os.path.abspath(__file__))), "plugins"))
        from loader import load_plugins
        plugins = load_plugins()
        name = step.get("name", "")
        if name not in plugins or not callable(plugins[name]):
            return False, f"plugin not found: {name}"
        try:
            ok, detail = plugins[name](api_base, step.get("params", {}))
            return bool(ok), f"plugin {name}: {detail}"
        except Exception as e:
            return False, f"plugin {name} error: {e}"
    if kind == "assert":
        _, sit = api(api_base, "GET", "/api/situation")
        check = next((c for c in sit.get("checks", [])
                      if c["name"] == step["check"]), None)
        if check is None:
            return False, f"unknown check {step['check']}"
        ok = check["verdict"] == step["verdict"]
        return ok, f"{step['check']} is {check['verdict']} (expect {step['verdict']})"
    return False, f"unknown action {kind}"


def run_file(path, api_base):
    with open(path) as f:
        exp = yaml.safe_load(f)
    results = []
    for i, step in enumerate(exp.get("steps", [])):
        try:
            ok, detail = run_step(api_base, step)
        except Exception as e:
            ok, detail = False, f"error: {e}"
        results.append({"step": i, "action": step.get("action"), "ok": ok,
                        "detail": detail})
        print(f"[{i}] {step.get('action')}: {'ok' if ok else 'FAIL'} — {detail}")
        if not ok and exp.get("stop_on_fail", True):
            break
    # always attempt cleanup
    try:
        api(api_base, "POST", "/chaos", {"latency_ms": 0, "error_rate": 0.0})
    except Exception:
        pass
    passed = all(r["ok"] for r in results)
    report = {"experiment": exp.get("name", path), "passed": passed,
              "results": results}
    out = os.path.splitext(path)[0] + ".report.json"
    with open(out, "w") as f:
        json.dump(report, f, indent=2)
    print(("PASS" if passed else "FAIL") + f" — report: {out}")
    return passed


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("file")
    p.add_argument("--api", default="http://localhost:8000")
    a = p.parse_args(argv)
    sys.exit(0 if run_file(a.file, a.api) else 1)


if __name__ == "__main__":
    main()
