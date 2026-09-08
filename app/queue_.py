"""Queue: Redis list if REDIS_URL set, else stdlib Queue (in-process)."""
import os
import json
import queue as stdq

_q = stdq.Queue()
_r = None
REDIS_QKEY = "lab:jobs"

try:
    import redis
    url = os.getenv("REDIS_URL")
    if url:
        _r = redis.Redis.from_url(url, decode_responses=True)
        _r.ping()
except Exception:
    _r = None


def enqueue(job: dict):
    payload = json.dumps(job)
    if _r is not None:
        _r.rpush(REDIS_QKEY, payload)
    else:
        _q.put(payload)


def dequeue(timeout: int = 1):
    if _r is not None:
        item = _r.blpop(REDIS_QKEY, timeout=timeout)
        return item[1] if item else None
    try:
        return _q.get(timeout=timeout)
    except stdq.Empty:
        return None


def qdepth():
    if _r is not None:
        try:
            return _r.llen(REDIS_QKEY)
        except Exception:
            pass
    return _q.qsize()


def provider():
    return "redis" if _r is not None else "memory"
