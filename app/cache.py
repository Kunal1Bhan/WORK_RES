"""Cache: Redis if REDIS_URL set, else in-memory dict (for simple local dev)."""
import os
import time

_store = {}
_expiry = {}

try:
    import redis
    _redis_url = os.getenv("REDIS_URL")
    _r = redis.Redis.from_url(_redis_url, decode_responses=True) if _redis_url else None
    if _r is not None:
        _r.ping()
except Exception:
    _r = None


def cache_get(key: str):
    if _r is not None:
        return _r.get(key)
    exp = _expiry.get(key)
    if exp and exp < time.time():
        _store.pop(key, None)
        _expiry.pop(key, None)
        return None
    return _store.get(key)


def cache_set(key: str, value: str, ttl: int = 60):
    if _r is not None:
        return _r.set(key, value, ex=ttl)
    _store[key] = value
    _expiry[key] = time.time() + ttl


def cache_stats():
    if _r is not None:
        try:
            return {"provider": "redis", "keys": _r.dbsize()}
        except Exception:
            pass
    return {"provider": "memory", "keys": len(_store)}
