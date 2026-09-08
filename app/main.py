"""FastAPI service: orders API + health + chaos hooks, production-hardened."""
import json
import random
import threading
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import cache as cache_mod
from . import metrics as m
from . import queue_ as q
from . import telemetry as tel
from .config import settings
from .db import Order, get_session, init_db

import logging
log = tel.setup_logging(getattr(logging, settings.LOG_LEVEL, logging.INFO))
_trace = tel.setup_tracing()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    log.info("startup complete")
    yield
    log.info("shutdown complete")


app = FastAPI(title="reliability-lab-api", lifespan=lifespan,
              docs_url="/docs", redoc_url="/redoc")

if _trace and _trace[0] == "fastapi":
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        FastAPIInstrumentor.instrument_app(app)
        log.info("otel fastapi instrumentation enabled")
    except Exception as e:
        log.info(f"otel instrumentation skipped: {e}")
elif _trace:
    log.info("otel manual tracer enabled (no fastapi auto-instrumentation)")
else:
    log.info("otel tracing disabled (set OTEL_ENABLED=1 to enable)")


def err(code, message, status):
    return JSONResponse({"error": {"code": code, "message": message}},
                        status_code=status)


@app.exception_handler(StarletteHTTPException)
async def _http_handler(request: Request, exc: StarletteHTTPException):
    return err(f"http_{exc.status_code}", str(exc.detail), exc.status_code)


@app.exception_handler(RequestValidationError)
async def _validation_handler(request: Request, exc: RequestValidationError):
    return err("validation_error", "invalid request body", 422)


@app.exception_handler(Exception)
async def _unhandled_handler(request: Request, exc: Exception):
    log.error(f"unhandled error path={request.url.path} exc={type(exc).__name__}: {exc}")
    return err("internal_error", "internal error", 500)


# Failure-injection knobs (set via /chaos, used by failurectl)
INJECT = {"latency_ms": 0, "error_rate": 0.0}


class OrderIn(BaseModel):
    item: str = Field(min_length=1, max_length=200)


# ---- middleware: request id + metrics + security headers ----
@app.middleware("http")
async def _mw(request: Request, call_next):
    rid = request.headers.get("X-Request-ID", uuid.uuid4().hex[:12])
    start = time.time()
    resp = await call_next(request)
    dur = time.time() - start
    m.REQUESTS.labels(request.method, request.url.path, str(resp.status_code)).inc()
    m.LATENCY.labels(request.url.path).observe(dur)
    resp.headers["X-Request-ID"] = rid
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    return resp


# ---- middleware: optional API key + rate limit ----
_buckets = {}
_buckets_lock = threading.Lock()


def _rate_ok(ip):
    if settings.RATE_LIMIT_RPS <= 0:
        return True
    now = time.time()
    with _buckets_lock:
        tokens, last = _buckets.get(ip, (settings.RATE_LIMIT_BURST, now))
        tokens = min(settings.RATE_LIMIT_BURST,
                     tokens + (now - last) * settings.RATE_LIMIT_RPS)
        if tokens < 1:
            _buckets[ip] = (tokens, now)
            return False
        _buckets[ip] = (tokens - 1, now)
        return True


@app.middleware("http")
async def _guard_mw(request: Request, call_next):
    path = request.url.path
    needs_key = settings.API_KEY and (
        path.startswith("/api/") or path == "/chaos")
    if needs_key and request.headers.get("X-API-Key") != settings.API_KEY:
        m.REQUESTS.labels(request.method, path, "401").inc()
        return err("unauthorized", "valid X-API-Key required", 401)
    if not _rate_ok(request.client.host if request.client else "?"):
        m.REQUESTS.labels(request.method, path, "429").inc()
        return err("rate_limited", "too many requests", 429)
    return await call_next(request)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/live")
def live():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    try:
        s = get_session()
        try:
            s.execute(text("SELECT 1"))
        finally:
            s.close()
        m.DB_UP.set(1)
        db = "up"
    except Exception as e:
        log.error(f"readiness db check failed: {type(e).__name__}")
        m.DB_UP.set(0)
        db = "down"
    m.QUEUE_DEPTH.set(q.qdepth())
    return {"db": db, "queue_provider": q.provider(),
            "cache": cache_mod.cache_stats(), "queue_depth": q.qdepth()}


@app.get("/metrics")
def metrics():
    return Response(m.metrics_payload(), media_type=m.metrics_content_type())


@app.post("/api/orders", status_code=201)
def create_order(o: OrderIn):
    if INJECT["latency_ms"]:
        time.sleep(INJECT["latency_ms"] / 1000.0)
    if INJECT["error_rate"] and random.random() < INJECT["error_rate"]:
        return err("injected_failure", "injected failure (chaos)", 500)
    s = get_session()
    try:
        row = Order(item=o.item, status="pending")
        s.add(row)
        s.commit()
        oid = row.id
    except Exception as e:
        s.rollback()
        log.error(f"order create failed: {type(e).__name__}")
        return err("db_error", "could not create order", 503)
    finally:
        s.close()
    q.enqueue({"order_id": oid, "item": o.item})
    m.ORDERS_CREATED.inc()
    log.info(f"order created id={oid} item={o.item}")
    return JSONResponse({"id": oid, "status": "pending"}, status_code=201,
                        headers={"Location": f"/api/orders/{oid}"})


@app.get("/api/orders")
def list_orders(limit: int = 20, offset: int = 0):
    limit = max(1, min(limit, settings.PAGE_SIZE_MAX))
    offset = max(0, offset)
    s = get_session()
    try:
        total = s.query(Order).count()
        rows = (s.query(Order).order_by(Order.id).offset(offset).limit(limit).all())
    finally:
        s.close()
    return {"total": total, "limit": limit, "offset": offset,
            "items": [{"id": r.id, "item": r.item, "status": r.status} for r in rows]}


@app.get("/api/orders/{oid}")
def get_order(oid: int):
    ck = f"order:{oid}"
    hit = cache_mod.cache_get(ck)
    if hit:
        m.CACHE_HITS.inc()
        return json.loads(hit)
    m.CACHE_MISSES.inc()
    s = get_session()
    try:
        row = s.query(Order).filter(Order.id == oid).first()
    finally:
        s.close()
    if not row:
        return err("not_found", "order not found", 404)
    out = {"id": row.id, "item": row.item, "status": row.status}
    cache_mod.cache_set(ck, json.dumps(out), ttl=30)
    return out


@app.post("/chaos")
def set_chaos(body: dict):
    """Failure-injection hook (dev/lab). Disable in prod via CHAOS_ENABLED=0."""
    if not settings.CHAOS_ENABLED:
        return err("forbidden", "chaos endpoint disabled", 403)
    if "latency_ms" in body:
        try:
            ms = int(body["latency_ms"])
        except (TypeError, ValueError):
            return err("validation_error", "latency_ms must be an integer", 422)
        if ms < 0:
            return err("validation_error", "latency_ms must be >= 0", 422)
        INJECT["latency_ms"] = ms
    if "error_rate" in body:
        try:
            rate = float(body["error_rate"])
        except (TypeError, ValueError):
            return err("validation_error", "error_rate must be a number", 422)
        if not 0.0 <= rate <= 1.0:
            return err("validation_error", "error_rate must be in [0, 1]", 422)
        INJECT["error_rate"] = rate
    return {"inject": INJECT}


@app.get("/")
def root():
    return {"service": "reliability-lab", "docs": "/docs",
            "dashboard": "/dashboard", "health": "/health"}


@app.get("/dashboard", response_class=FileResponse)
def dashboard():
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    return FileResponse(os.path.join(here, "static", "dashboard.html"),
                        media_type="text/html")
