#!/usr/bin/env python3
"""slo.py — compute availability + latency p50/p95/p99 from an access log.
Log format (one JSON per line): {"status": 200, "latency": 0.123}
Usage: python slo-engine/slo.py --log requests.jsonl --target 99.9
"""
import argparse
import json
import sys


def percentile(data, p):
    if not data:
        return 0.0
    s = sorted(data)
    k = (len(s) - 1) * p / 100
    f, c = int(k), min(int(k) + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


def evaluate(entries, target=99.9):
    total = len(entries)
    good = sum(1 for e in entries if e.get("status", 500) < 500)
    avail = 100.0 * good / total if total else 0.0
    lats = [float(e.get("latency", 0)) for e in entries]
    p50, p95, p99 = percentile(lats, 50), percentile(lats, 95), percentile(lats, 99)
    remaining = avail - target  # >= 0 means budget remains
    return {"total": total, "availability_pct": round(avail, 3),
            "p50": round(p50, 4), "p95": round(p95, 4), "p99": round(p99, 4),
            "target": target, "error_budget_remaining": round(remaining, 3),
            "verdict": "PASS" if remaining >= 0 else "FAIL"}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--log", required=True)
    p.add_argument("--target", type=float, default=99.9)
    a = p.parse_args(argv)
    try:
        with open(a.log) as f:
            entries = [json.loads(line) for line in f if line.strip()]
    except FileNotFoundError:
        print(f"error: log file not found: {a.log}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"error: invalid JSON in {a.log}: {e}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(evaluate(entries, a.target), indent=2))


if __name__ == "__main__":
    main()
