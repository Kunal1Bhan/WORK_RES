#!/usr/bin/env python3
"""router.py — weighted traffic router with health checks + failover (M7 sim).
Routes requests across regions (API base URLs); unhealthy regions get zero
weight; all-down returns 502.

Usage: python traffic-engine/router.py --regions http://a:8000,http://b:8001
Runs a small proxy on --port (default 8090). GET /route?path=/health proxies.
"""
import argparse
import json
import random
import urllib.request


def check(url, timeout=2):
    try:
        with urllib.request.urlopen(url + "/health", timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def pick(weights):
    total = sum(weights)
    if total <= 0:
        return None
    x = random.random() * total
    for i, w in enumerate(weights):
        x -= w
        if x <= 0:
            return i
    return len(weights) - 1


class Router:
    def __init__(self, regions, weights=None):
        self.regions = regions
        self.base_weights = weights or [1.0] * len(regions)
        self.healthy = [True] * len(regions)

    def refresh(self):
        self.healthy = [check(u) for u in self.regions]
        return self.healthy

    def effective_weights(self):
        return [b if h else 0.0 for b, h in zip(self.base_weights, self.healthy)]

    def route(self, path="/health"):
        idx = pick(self.effective_weights())
        if idx is None:
            return 502, {"error": "all regions down"}
        url = self.regions[idx] + path
        try:
            with urllib.request.urlopen(url, timeout=5) as r:
                return r.status, r.read().decode()
        except Exception as e:
            code = getattr(e, "code", 502) or 502
            return code, {"error": str(e), "region": self.regions[idx]}


def main(argv=None):
    from http.server import BaseHTTPRequestHandler, HTTPServer
    p = argparse.ArgumentParser()
    p.add_argument("--regions", default="http://localhost:8000")
    p.add_argument("--port", type=int, default=8090)
    a = p.parse_args(argv)
    router = Router(a.regions.split(","))

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            router.refresh()
            path = self.path.replace("/route?path=", "").replace("/route", "/health")
            status, body = router.route(path if path.startswith("/") else "/health")
            data = body.encode() if isinstance(body, str) else json.dumps(body).encode()
            self.send_response(status if isinstance(status, int) else 200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    print(f"router on :{a.port} regions={router.regions}", flush=True)
    HTTPServer(("0.0.0.0", a.port), H).serve_forever()


if __name__ == "__main__":
    main()
