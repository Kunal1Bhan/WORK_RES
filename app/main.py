"""FastAPI service: orders API + health + chaos hooks, production-hardened."""
import json
import logging
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
from . import signals as sig
from . import telemetry as tel
from .config import settings
from .db import Order, Product, Event, get_session, init_db, log_event, PROMOS

LOW_STOCK_AT = 5

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
    item: str = Field(default="", max_length=200)
    product_id: int | None = None
    qty: int = Field(default=1, ge=1, le=100)
    promo: str | None = Field(default=None, max_length=20)


class ProductIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    price_cents: int = Field(ge=0)
    stock: int = Field(ge=0)


class RestockIn(BaseModel):
    qty: int = Field(ge=1, le=10000)


# ---- middleware: request id + metrics + security headers ----
@app.middleware("http")
async def _mw(request: Request, call_next):
    rid = request.headers.get("X-Request-ID", uuid.uuid4().hex[:12])
    start = time.time()
    resp = await call_next(request)
    dur = time.time() - start
    m.REQUESTS.labels(request.method, request.url.path, str(resp.status_code)).inc()
    m.LATENCY.labels(request.url.path).observe(dur)
    sig.record(resp.status_code, dur)
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
    return ready_body()


def ready_body():
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
    promo = (o.promo or "").strip().upper() or None
    if promo and promo not in PROMOS:
        return err("validation_error", f"unknown promo code (try: {', '.join(PROMOS)})", 422)
    s = get_session()
    try:
        if o.product_id is not None:
            prod = s.query(Product).filter(Product.id == o.product_id).first()
            if not prod:
                return err("not_found", "product not found", 404)
            if prod.stock < o.qty:
                return err("out_of_stock",
                            f"only {prod.stock} of {prod.name} left", 409)
            discount = PROMOS.get(promo, 0.0)
            total = int(round(prod.price_cents * o.qty * (1 - discount)))
            prod.stock -= o.qty
            row = Order(item=prod.name, status="pending", product_id=prod.id,
                        qty=o.qty, total_cents=total, promo=promo)
            if prod.stock < LOW_STOCK_AT:
                log_event(s, "stock_low", f"{prod.name}: {prod.stock} left")
        else:
            if not o.item.strip():
                return err("validation_error",
                            "item is required (1-200 chars) without product_id", 422)
            row = Order(item=o.item.strip(), status="pending", qty=o.qty,
                        total_cents=0, promo=promo)
        s.add(row)
        s.commit()
        oid = row.id
        item, total = row.item, row.total_cents
        log_event(s, "order_created", f"#{oid} {item} x{row.qty}")
        s.commit()
    except Exception as e:
        s.rollback()
        log.error(f"order create failed: {type(e).__name__}")
        return err("db_error", "could not create order", 503)
    finally:
        s.close()
    q.enqueue({"order_id": oid, "item": item})
    m.ORDERS_CREATED.inc()
    log.info(f"order created id={oid} item={item}")
    return JSONResponse({"id": oid, "status": "pending",
                         "total_cents": total},
                        status_code=201, headers={"Location": f"/api/orders/{oid}"})


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
            "items": [{"id": r.id, "item": r.item, "status": r.status,
                       "product_id": r.product_id, "qty": r.qty,
                       "total_cents": r.total_cents, "promo": r.promo}
                      for r in rows]}


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
    out = {"id": row.id, "item": row.item, "status": row.status,
           "product_id": row.product_id, "qty": row.qty,
           "total_cents": row.total_cents, "promo": row.promo}
    cache_mod.cache_set(ck, json.dumps(out), ttl=30)
    return out


@app.post("/api/orders/{oid}/cancel")
def cancel_order(oid: int):
    s = get_session()
    try:
        row = s.query(Order).filter(Order.id == oid).first()
        if not row:
            return err("not_found", "order not found", 404)
        if row.status != "pending":
            return err("conflict",
                        f"only pending orders can cancel (is {row.status})", 409)
        row.status = "cancelled"
        if row.product_id is not None:
            prod = s.query(Product).filter(Product.id == row.product_id).first()
            if prod:
                prod.stock += row.qty
        log_event(s, "order_cancelled", f"#{oid} {row.item} x{row.qty}")
        s.commit()
    finally:
        s.close()
    cache_mod.cache_delete(f"order:{oid}")
    return {"id": oid, "status": "cancelled"}


@app.get("/api/products")
def list_products():
    s = get_session()
    try:
        rows = s.query(Product).order_by(Product.id).all()
    finally:
        s.close()
    return {"items": [{"id": p.id, "name": p.name, "price_cents": p.price_cents,
                       "stock": p.stock, "low": p.stock < LOW_STOCK_AT}
                      for p in rows]}


@app.post("/api/products", status_code=201)
def create_product(p: ProductIn):
    s = get_session()
    try:
        if s.query(Product).filter(Product.name == p.name).first():
            return err("conflict", "product name already exists", 409)
        row = Product(name=p.name, price_cents=p.price_cents, stock=p.stock)
        s.add(row)
        s.commit()
        pid = row.id
        log_event(s, "product_created", f"{p.name} @ {p.price_cents}c x{p.stock}")
        s.commit()
    finally:
        s.close()
    return JSONResponse({"id": pid}, status_code=201,
                        headers={"Location": f"/api/products/{pid}"})


@app.post("/api/products/{pid}/restock")
def restock(pid: int, body: RestockIn):
    s = get_session()
    try:
        row = s.query(Product).filter(Product.id == pid).first()
        if not row:
            return err("not_found", "product not found", 404)
        row.stock += body.qty
        stock = row.stock
        log_event(s, "restocked", f"{row.name} +{body.qty} = {stock}")
        s.commit()
    finally:
        s.close()
    return {"id": pid, "stock": stock}


@app.get("/api/stats")
def stats():
    from sqlalchemy import func
    s = get_session()
    try:
        revenue = s.query(func.coalesce(func.sum(Order.total_cents), 0)).filter(
            Order.status == "done").scalar()
        counts = dict(s.query(Order.status, func.count(Order.id))
                      .group_by(Order.status).all())
        low = s.query(Product).filter(Product.stock < LOW_STOCK_AT).all()
    finally:
        s.close()
    m.REVENUE_CENTS.set(revenue)
    m.LOW_STOCK.set(len(low))
    return {"revenue_cents": revenue, "by_status": counts,
            "low_stock": [{"id": p.id, "name": p.name, "stock": p.stock}
                          for p in low]}


@app.get("/api/events")
def events(limit: int = 15):
    limit = max(1, min(limit, 100))
    s = get_session()
    try:
        rows = (s.query(Event).order_by(Event.id.desc()).limit(limit).all())
    finally:
        s.close()
    return {"items": [{"id": e.id, "ts": e.ts.isoformat() if e.ts else None,
                       "kind": e.kind, "detail": e.detail} for e in rows]}


@app.get("/api/situation")
def situation():
    """Deduction report: live signals vs SLOs + verdicts + recommendations."""
    snap = sig.snapshot()
    ready = ready_body()
    chaos = {"latency_ms": INJECT["latency_ms"], "error_rate": INJECT["error_rate"]}
    chaos_active = bool(chaos["latency_ms"] or chaos["error_rate"])
    checks = []
    recs = []

    avail_ok = snap["availability_pct"] >= sig.SLO_AVAILABILITY
    checks.append({"name": "availability", "value": snap["availability_pct"],
                   "target": sig.SLO_AVAILABILITY, "unit": "%",
                   "verdict": "PASS" if avail_ok else "FAIL"})
    if not avail_ok:
        recs.append("Availability below 99.9% — inspect 5xx sources, then remediate.")

    p95_ok = snap["p95_ms"] <= sig.SLO_P95_MS
    checks.append({"name": "latency_p95", "value": snap["p95_ms"],
                   "target": sig.SLO_P95_MS, "unit": "ms",
                   "verdict": "PASS" if p95_ok else "FAIL"})
    if not p95_ok:
        recs.append("p95 latency breaching 500ms — check DB/cache latency and injected delays.")

    qd = ready["queue_depth"]
    q_ok = qd <= sig.SLO_QUEUE_MAX
    checks.append({"name": "queue_depth", "value": qd,
                   "target": sig.SLO_QUEUE_MAX, "unit": "orders",
                   "verdict": "PASS" if q_ok else "FAIL"})
    if not q_ok:
        recs.append("Queue backlog growing — scale workers (competing consumers).")

    db_ok = ready["db"] == "up"
    checks.append({"name": "database", "value": ready["db"], "target": "up",
                   "unit": "", "verdict": "PASS" if db_ok else "FAIL"})
    if not db_ok:
        recs.append("Database unreachable — check Postgres container and DATABASE_URL.")

    checks.append({"name": "chaos", "value": "active" if chaos_active else "clear",
                   "target": "clear", "unit": "",
                   "verdict": "WARN" if chaos_active else "PASS"})
    if chaos_active:
        recs.append(f"Failure injection ACTIVE {chaos} — clear with failurectl when done drilling.")

    stats_body = stats()
    if stats_body["low_stock"]:
        names = ", ".join(p["name"] for p in stats_body["low_stock"])
        checks.append({"name": "stock", "value": len(stats_body["low_stock"]),
                       "target": 0, "unit": "low products", "verdict": "WARN"})
        recs.append(f"Low stock: {names} — restock soon.")
    else:
        checks.append({"name": "stock", "value": 0, "target": 0,
                       "unit": "low products", "verdict": "PASS"})

    failing = sum(1 for c in checks if c["verdict"] == "FAIL")
    warned = sum(1 for c in checks if c["verdict"] == "WARN")
    if failing:
        summary = f"ATTENTION: {failing} SLO check(s) failing, {warned} warning(s). {recs[0] if recs else ''}"
    elif warned:
        summary = f"Stable with {warned} warning(s). {recs[0] if recs else ''}"
    else:
        summary = (f"All systems nominal: {snap['availability_pct']}% availability, "
                   f"p95 {snap['p95_ms']}ms, queue {qd}, revenue "
                   f"${stats_body['revenue_cents']/100:.2f}.")
    return {"traffic": snap, "chaos": chaos, "dependencies": ready,
            "revenue_cents": stats_body["revenue_cents"],
            "checks": checks, "recommendations": recs, "summary": summary}


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
    if INJECT["latency_ms"] or INJECT["error_rate"]:
        _note_event("chaos_set", str(INJECT))
    else:
        _note_event("chaos_cleared", "")
    return {"inject": INJECT}


def _note_event(kind, detail):
    try:
        s = get_session()
        try:
            log_event(s, kind, detail)
            s.commit()
        finally:
            s.close()
    except Exception:
        pass


@app.get("/")
def root():
    return {"service": "reliability-lab", "docs": "/docs",
            "dashboard": "/dashboard", "topology": "/topology", "health": "/health"}


@app.get("/dashboard", response_class=FileResponse)
def dashboard():
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    return FileResponse(os.path.join(here, "static", "dashboard.html"),
                        media_type="text/html")


@app.get("/topology", response_class=FileResponse)
def topology():
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    return FileResponse(os.path.join(here, "static", "topology.html"),
                        media_type="text/html")
