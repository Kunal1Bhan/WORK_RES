#!/usr/bin/env python3
"""failurectl — minimal failure injection CLI (LEVEL 1 Failure Engineering).
Usage:
  python failure-engine/failurectl.py latency --ms 500 [--api URL]
  python failure-engine/failurectl.py error --rate 0.5 [--api URL]
  python failure-engine/failurectl.py clear [--api URL]
  python failure-engine/failurectl.py cpu --seconds 5   (local CPU burn, no server needed)
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request


def _post(api: str, body: dict):
    req = urllib.request.Request(api + "/chaos", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            print(r.read().decode())
    except urllib.error.HTTPError as e:
        print(f"error: server returned {e.code}: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"error: cannot reach API at {api}: {e.reason}", file=sys.stderr)
        sys.exit(1)


DEFAULT_API = "http://localhost:8000"


def main(argv=None):
    # --api accepted both before and after the subcommand; an explicit
    # post-subcommand value wins, otherwise the pre-subcommand/global one.
    api_after = argparse.ArgumentParser(add_help=False)
    api_after.add_argument("--api", default=argparse.SUPPRESS)
    p = argparse.ArgumentParser(prog="failurectl")
    p.add_argument("--api", default=DEFAULT_API)
    sub = p.add_subparsers(dest="cmd", required=True)
    lat_p = sub.add_parser("latency", parents=[api_after])
    lat_p.add_argument("--ms", type=int, default=500)
    err_p = sub.add_parser("error", parents=[api_after])
    err_p.add_argument("--rate", type=float, default=0.5)
    sub.add_parser("clear", parents=[api_after])
    cpu_p = sub.add_parser("cpu", parents=[api_after])
    cpu_p.add_argument("--seconds", type=int, default=5)
    a = p.parse_args(argv)

    if a.cmd == "latency":
        if a.ms < 0:
            p.error("--ms must be >= 0")
        _post(a.api, {"latency_ms": a.ms})
        print(f"event=injected_latency ms={a.ms}")
    elif a.cmd == "error":
        if not 0.0 <= a.rate <= 1.0:
            p.error("--rate must be in [0, 1]")
        _post(a.api, {"error_rate": a.rate})
        print(f"event=injected_errors rate={a.rate}")
    elif a.cmd == "clear":
        _post(a.api, {"latency_ms": 0, "error_rate": 0.0})
        print("event=chaos_cleared")
    elif a.cmd == "cpu":
        if a.seconds <= 0:
            p.error("--seconds must be > 0")
        end = time.time() + a.seconds
        x = 0
        while time.time() < end:
            x += sum(i * i for i in range(500))
        print(f"event=cpu_burn seconds={a.seconds} checksum={x % 97}")


if __name__ == "__main__":
    main()
