"""End-to-end: real uvicorn + real worker subprocesses, full user journey.

Journey: health -> create order -> worker marks done -> chaos 500s ->
remediate -> healthy again -> list shows orders. Skipped if ports busy.
"""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request

import pytest

LAB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "http://127.0.0.1:8133"
ENV = dict(os.environ, DATABASE_URL="sqlite:///" + os.path.join(LAB, "e2e.db"),
             REDIS_URL="redis://127.0.0.1:6379/15")  # isolated redis db


def free():
    try:
        socket.create_connection(("127.0.0.1", 8133), timeout=1).close()
        return False
    except OSError:
        return True


def redis_up():
    try:
        socket.create_connection(("127.0.0.1", 6379), timeout=1).close()
        return True
    except OSError:
        return False


# The file queue is per-process: a real E2E drain needs a shared broker.
needs_broker = pytest.mark.skipif(not redis_up(), reason="no Redis on 127.0.0.1:6379")


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data,
                                 headers={"Content-Type": "application/json"},
                                 method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


import urllib.error  # noqa: E402


def wait_healthy(deadline=40):
    t0 = time.time()
    while time.time() - t0 < deadline:
        try:
            if call("GET", "/health")[0] == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


@pytest.mark.skipif(not free(), reason="port 8133 busy")
@needs_broker
def test_full_journey(tmp_path):
    for f in ("e2e.db",):
        try:
            os.remove(os.path.join(LAB, f))
        except FileNotFoundError:
            pass
    api = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app",
                            "--host", "127.0.0.1", "--port", "8133"],
                           cwd=LAB, env=ENV, stdout=subprocess.DEVNULL,
                           stderr=subprocess.STDOUT)
    worker = subprocess.Popen([sys.executable, "-m", "app.worker"],
                              cwd=LAB, env=ENV, stdout=subprocess.DEVNULL,
                              stderr=subprocess.STDOUT)
    try:
        assert wait_healthy(), "API never became healthy"
        assert call("GET", "/ready")[0] == 200

        code, text = call("POST", "/api/orders", {"item": "e2e-book"})
        assert code == 201, text
        oid = json.loads(text)["id"]

        # worker drains the real queue: poll until done (up to 20s)
        done = False
        for _ in range(20):
            time.sleep(1)
            c2, t2 = call("GET", f"/api/orders/{oid}")
            # NOTE: 30s cache may serve stale 'pending'; bust via list endpoint
            items = json.loads(call("GET", "/api/orders?limit=100")[1])["items"]
            row = next(i for i in items if i["id"] == oid)
            if row["status"] == "done":
                done = True
                break
        assert done, "worker did not mark order done"

        # failure path: inject, observe 500 + envelope, remediate via clear
        assert call("POST", "/chaos", {"error_rate": 1.0})[0] == 200
        c3, t3 = call("POST", "/api/orders", {"item": "bad"})
        assert c3 == 500 and json.loads(t3)["error"]["code"] == "injected_failure"
        assert call("POST", "/chaos", {"error_rate": 0.0})[0] == 200
        assert call("POST", "/api/orders", {"item": "good"})[0] == 201

        # validation path
        assert call("POST", "/api/orders", {"item": ""})[0] == 422
        assert call("GET", "/api/orders/424242")[0] == 404
    finally:
        worker.terminate()
        api.terminate()
        worker.wait(timeout=10)
        api.wait(timeout=10)
        try:
            os.remove(os.path.join(LAB, "e2e.db"))
        except FileNotFoundError:
            pass
