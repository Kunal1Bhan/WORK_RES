"""Centralized environment configuration (prod: env vars / .env file).

All tunables in one place. `.env` in the repo root is loaded if present
(dev convenience); real deployments use process env. No secrets here.
"""
import os

LAB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_dotenv():
    path = os.path.join(LAB_DIR, ".env")
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


_load_dotenv()


def _get(name, default=""):
    return os.getenv(name, default)


def _get_int(name, default):
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _get_float(name, default):
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _get_bool(name, default):
    return os.getenv(name, "1" if default else "0").lower() in ("1", "true", "yes")


class Settings:
    DATABASE_URL = _get("DATABASE_URL", "sqlite:///./lab.db")
    REDIS_URL = _get("REDIS_URL", "")
    API_KEY = _get("API_KEY", "")  # empty = auth disabled (local dev)
    TEAMS_FILE = _get("LAB_TEAMS_FILE", "")
    CHAOS_ENABLED = _get_bool("CHAOS_ENABLED", True)
    RATE_LIMIT_RPS = _get_float("RATE_LIMIT_RPS", 0)  # 0 = disabled
    RATE_LIMIT_BURST = _get_int("RATE_LIMIT_BURST", 50)
    PAGE_SIZE_MAX = _get_int("PAGE_SIZE_MAX", 100)
    POOL_SIZE = _get_int("POOL_SIZE", 5)
    POOL_MAX_OVERFLOW = _get_int("POOL_MAX_OVERFLOW", 10)
    LOG_LEVEL = _get("LOG_LEVEL", "INFO").upper()
    OTEL_ENABLED = _get_bool("OTEL_ENABLED", False)


settings = Settings()


_teams_cache = {"mtime": 0, "data": {}}


def load_teams():
    """Return {key: {team, role}}. Empty = teams disabled. Cached by mtime."""
    import yaml as _yaml
    path = settings.TEAMS_FILE
    if not path or not os.path.exists(path):
        return {}
    try:
        mtime = os.path.getmtime(path)
        if mtime == _teams_cache["mtime"]:
            return _teams_cache["data"]
        with open(path) as f:
            data = _yaml.safe_load(f) or {}
        out = {t["key"]: {"team": t.get("team", "?"), "role": t.get("role", "member")}
               for t in data.get("teams", []) if t.get("key")}
        _teams_cache.update(mtime=mtime, data=out)
        return out
    except Exception:
        return {}
