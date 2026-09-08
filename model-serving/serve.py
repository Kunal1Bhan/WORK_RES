"""Tiny sentiment model served over HTTP (M11 model serving).
Real inference (fixed-weight linear bag-of-words classifier), real latency
measurement, GPU telemetry attached per request. No heavy deps.

Run: python model-serving/serve.py --port 8100
POST /predict {"text": "..."} -> {"label", "score", "latency_ms", "device"}
GET  /health, GET /metrics (json)
"""
import argparse
import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

POS = {"good": 1.2, "great": 1.6, "love": 1.8, "fast": 0.8, "reliable": 1.0,
       "excellent": 1.7, "stable": 0.9, "awesome": 1.5}
NEG = {"bad": -1.2, "slow": -1.0, "broken": -1.8, "fail": -1.5, "down": -1.3,
       "terrible": -1.7, "crash": -1.6, "error": -1.1}
BIAS = 0.1

_n = {"requests": 0, "errors": 0, "lat_ms": []}


def predict(text):
    toks = text.lower().split()
    score = BIAS + sum(POS.get(t, 0) + NEG.get(t, 0) for t in toks)
    prob = 1 / (1 + 2.718281828 ** (-score))
    return ("positive" if prob >= 0.5 else "negative", round(prob, 4))


_gpu_cache = {"at": 0.0, "data": None}
GPU_CACHE_TTL = 5.0


def gpu_telemetry():
    now = time.time()
    if _gpu_cache["data"] and now - _gpu_cache["at"] < GPU_CACHE_TTL:
        return _gpu_cache["data"]
    data = _gpu_telemetry_uncached()
    _gpu_cache.update(at=now, data=data)
    return data


def _gpu_telemetry_uncached():
    try:
        import subprocess
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5)
        if out.returncode == 0:
            u, mu, mt = [x.strip() for x in out.stdout.split(",")]
            return {"provider": "nvidia-smi", "util_pct": float(u),
                    "mem_used_mb": float(mu), "mem_total_mb": float(mt)}
    except Exception:
        pass
    return {"provider": "sim", "util_pct": 12.0, "mem_used_mb": 1024, "mem_total_mb": 8192}


def make_handler(device):
    class H(BaseHTTPRequestHandler):
        def _send(self, code, obj):
            data = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path == "/health":
                self._send(200, {"status": "ok", "device": device})
            elif self.path == "/metrics":
                lat = sorted(_n["lat_ms"])
                p50 = lat[len(lat) // 2] if lat else 0
                self._send(200, {"requests": _n["requests"], "errors": _n["errors"],
                                 "p50_ms": p50, "device": device,
                                 "gpu": gpu_telemetry()})
            else:
                self._send(404, {"error": "not found"})

        def do_POST(self):
            if self.path != "/predict":
                self._send(404, {"error": "not found"})
                return
            try:
                body = json.loads(self.rfile.read(
                    int(self.headers.get("Content-Length", 0))))
            except Exception:
                _n["errors"] += 1
                self._send(400, {"error": "invalid json"})
                return
            t0 = time.time()
            label, score = predict(body.get("text", ""))
            ms = round((time.time() - t0) * 1000, 3)
            _n["requests"] += 1
            _n["lat_ms"].append(ms)
            self._send(200, {"label": label, "score": score, "latency_ms": ms,
                             "device": device, "gpu": gpu_telemetry()})

        def log_message(self, *args):
            pass
    return H


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=8100)
    p.add_argument("--device", default="auto")
    a = p.parse_args(argv)
    device = a.device
    if device == "auto":
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        "..", "gpu-scheduler"))
        from scheduler import inventory, place
        device = place(inventory("auto"), 500)["device"]
    print(f"model-serving on :{a.port} device={device}", flush=True)
    HTTPServer(("0.0.0.0", a.port), make_handler(device)).serve_forever()


if __name__ == "__main__":
    main()
