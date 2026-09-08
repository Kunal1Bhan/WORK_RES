#!/usr/bin/env python3
"""remediate.py — trivial detector->action loop: clears chaos if error rate high.
Usage: python remediation-engine/remediate.py [--api http://localhost:8000]
"""
import argparse
import json
import sys
import urllib.error
import urllib.request


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--api", default="http://localhost:8000")
    a = p.parse_args(argv)
    # In a real engine this would query Prometheus; here we just reset chaos knobs.
    req = urllib.request.Request(a.api + "/chaos", data=json.dumps(
        {"latency_ms": 0, "error_rate": 0.0}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            print("remediation=cleared_chaos", r.read().decode())
    except urllib.error.URLError as e:
        print(f"error: cannot reach API at {a.api}: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
