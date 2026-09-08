#!/usr/bin/env python3
"""loadtest.py — minimal concurrent HTTP load generator (M10).
Hammers the API, records per-request latency/status, prints RPS + p50/p95/p99
and appends a JSONL log usable by slo.py.

Usage: python benchmarks/loadtest.py --base http://localhost:8000 --rps 50 --seconds 20
"""
import argparse
import json
import threading
import time
import urllib.request


def one(base, path, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data,
                                 headers={"Content-Type": "application/json"}, method=method)
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            r.read()
            return time.time() - start, r.status
    except Exception as e:
        code = getattr(e, "code", 0) or 0
        return time.time() - start, code


def worker(base, rps, seconds, out):
    interval = 1.0 / rps
    end = time.time() + seconds
    i = 0
    while time.time() < end:
        t0 = time.time()
        if i % 5 == 4:
            lat, st = one(base, "/api/orders", "POST", {"item": f"load-{i}"})
        else:
            lat, st = one(base, "/health")
        out.append({"status": st, "latency": round(lat, 4)})
        i += 1
        time.sleep(max(0.0, interval - (time.time() - t0)))


def percentile(data, p):
    s = sorted(data)
    k = (len(s) - 1) * p / 100
    f, c = int(k), min(int(k) + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--base", default="http://localhost:8000")
    p.add_argument("--rps", type=float, default=20)
    p.add_argument("--seconds", type=int, default=15)
    p.add_argument("--threads", type=int, default=4)
    p.add_argument("--out", default="benchmarks/results.jsonl")
    a = p.parse_args(argv)
    per_thread = max(1.0, a.rps / a.threads)
    buckets, threads = [], []
    t0 = time.time()
    for _ in range(a.threads):
        b = []
        buckets.append(b)
        t = threading.Thread(target=worker, args=(a.base, per_thread, a.seconds, b))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    dur = time.time() - t0
    rows = [r for b in buckets for r in b]
    lats = [r["latency"] for r in rows]
    ok = sum(1 for r in rows if 200 <= r["status"] < 300)
    with open(a.out, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    report = {
        "requests": len(rows), "ok": ok,
        "availability_pct": round(100.0 * ok / len(rows), 3) if rows else 0.0,
        "rps_achieved": round(len(rows) / dur, 1),
        "p50": round(percentile(lats, 50), 4) if lats else 0,
        "p95": round(percentile(lats, 95), 4) if lats else 0,
        "p99": round(percentile(lats, 99), 4) if lats else 0,
        "seconds": round(dur, 1), "log": a.out,
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
