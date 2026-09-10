"""Sample plugin (FR15): latency_spike — brief latency injection then clear."""
import json
import time
import urllib.request


def _post(api, body):
    req = urllib.request.Request(api + "/chaos", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.status


def register():
    def run(api, params):
        ms = int(params.get("ms", 300))
        seconds = float(params.get("seconds", 3))
        _post(api, {"latency_ms": ms, "error_rate": 0.0})
        time.sleep(seconds)
        _post(api, {"latency_ms": 0, "error_rate": 0.0})
        return True, f"latency spike {ms}ms for {seconds}s done"

    return {"name": "latency_spike", "run": run}
