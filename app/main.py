"""FastAPI service: API + health + orders + chaos hooks (LEVEL 1 workload)."""
import json
import random
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text

from . import cache as cache_mod
from . import metrics as m
from . import queue_ as q
from .db import Order, get_session, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="reliability-lab-api", lifespan=lifespan)

# Failure-injection knobs (set via /chaos, used by failurectl)
INJECT = {"latency_ms": 0, "error_rate": 0.0}


class OrderIn(BaseModel):
    item: str


@app.middleware("http")
async def _metrics_mw(request: Request, call_next):
    start = time.time()
    resp = await call_next(request)
    dur = time.time() - start
    m.REQUESTS.labels(request.method, request.url.path, str(resp.status_code)).inc()
    m.LATENCY.labels(request.url.path).observe(dur)
    return resp


@app.get("/health")
def health():
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
    except Exception:
        m.DB_UP.set(0)
        db = "down"
    m.QUEUE_DEPTH.set(q.qdepth())
    return {"db": db, "queue_provider": q.provider(),
            "cache": cache_mod.cache_stats(), "queue_depth": q.qdepth()}


@app.get("/metrics")
def metrics():
    return Response(m.metrics_payload(), media_type=m.metrics_content_type())


@app.post("/api/orders")
def create_order(o: OrderIn):
    # injected latency / errors (chaos testing)
    if INJECT["latency_ms"]:
        time.sleep(INJECT["latency_ms"] / 1000.0)
    if INJECT["error_rate"] and random.random() < INJECT["error_rate"]:
        return JSONResponse({"error": "injected failure"}, status_code=500)
    s = get_session()
    try:
        row = Order(item=o.item, status="pending")
        s.add(row)
        s.commit()
        oid = row.id
    finally:
        s.close()
    q.enqueue({"order_id": oid, "item": o.item})
    m.ORDERS_CREATED.inc()
    return {"id": oid, "status": "pending"}


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
        return JSONResponse({"error": "not found"}, status_code=404)
    out = {"id": row.id, "item": row.item, "status": row.status}
    cache_mod.cache_set(ck, json.dumps(out), ttl=30)
    return out


@app.post("/chaos")
def set_chaos(body: dict):
    """Simple chaos hook used by failurectl (dev only)."""
    if "latency_ms" in body:
        ms = int(body["latency_ms"])
        if ms < 0:
            return JSONResponse({"error": "latency_ms must be >= 0"}, status_code=422)
        INJECT["latency_ms"] = ms
    if "error_rate" in body:
        rate = float(body["error_rate"])
        if not 0.0 <= rate <= 1.0:
            return JSONResponse({"error": "error_rate must be in [0, 1]"}, status_code=422)
        INJECT["error_rate"] = rate
    return {"inject": INJECT}


@app.get("/")
def root():
    return {"service": "reliability-lab", "docs": "/docs", "health": "/health"}
