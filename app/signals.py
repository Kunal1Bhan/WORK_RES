"""Rolling in-app traffic signals (powers /api/situation).

Bounded deques: no unbounded growth. Thread-safe via lock.
Thresholds mirror slo-engine/slos.yaml (kept in sync by tests/test_slos.py
style checks would be overkill here — values documented below).
"""
import statistics
import threading
import time
from collections import deque

SLO_AVAILABILITY = 99.9
SLO_P95_MS = 500.0
SLO_QUEUE_MAX = 50

WINDOW = 300.0  # seconds of history kept
MAX_SAMPLES = 2000

_lock = threading.Lock()
_reqs = deque()  # (timestamp, status_code, latency_s)


def record(status, latency_s):
    now = time.time()
    with _lock:
        _reqs.append((now, int(status), float(latency_s)))
        while len(_reqs) > MAX_SAMPLES:
            _reqs.popleft()


def snapshot():
    now = time.time()
    with _lock:
        rows = [r for r in _reqs if now - r[0] <= WINDOW]
    total = len(rows)
    if not total:
        return {"requests": 0, "availability_pct": 100.0,
                "p50_ms": 0.0, "p95_ms": 0.0, "rps": 0.0}
    errors = sum(1 for _, st, _ in rows if st >= 500)
    lats = sorted(lat * 1000 for _, _, lat in rows)
    span = max(now - rows[0][0], 1.0)
    q = statistics.quantiles(lats, n=100) if len(lats) >= 100 else None
    p50 = statistics.median(lats)
    p95 = q[94] if q else lats[min(int(len(lats) * 0.95), len(lats) - 1)]
    return {"requests": total,
            "availability_pct": round(100.0 * (total - errors) / total, 3),
            "p50_ms": round(p50, 2), "p95_ms": round(p95, 2),
            "rps": round(total / span, 2)}
