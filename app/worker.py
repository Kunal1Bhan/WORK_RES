"""Background worker: consumes queue, marks orders done. Run: python -m app.worker"""
import json
import signal
import time

from .db import Order, get_session, init_db
from . import queue_ as q
from . import metrics as m

_running = True


def _stop(*_args):
    global _running
    _running = False


def process_one(payload: str) -> str:
    job = json.loads(payload)
    oid = job.get("order_id")
    time.sleep(0.05)  # simulate work
    s = get_session()
    try:
        row = s.query(Order).filter(Order.id == oid).first()
        if row is None:
            m.ORDERS_PROCESSED.labels("missing").inc()
            return "missing"
        if row.status != "pending":
            # cancelled (or already done): leave it alone
            m.ORDERS_PROCESSED.labels("skipped").inc()
            return "skipped"
        row.status = "done"
        s.commit()
        m.ORDERS_PROCESSED.labels("ok").inc()
        m.REVENUE_CENTS.inc(row.total_cents or 0)
        return "ok"
    except Exception:
        s.rollback()
        m.ORDERS_PROCESSED.labels("fail").inc()
        return "fail"
    finally:
        s.close()


def main():
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    init_db()
    print("worker started, provider=", q.provider(), flush=True)
    while _running:
        item = q.dequeue(timeout=2)
        if item:
            process_one(item)


if __name__ == "__main__":
    main()
