"""Shop features: catalog, promos, stock, cancel, stats, events feed."""
import pytest
from fastapi.testclient import TestClient

import app.main as mainmod
from app.db import init_db
from app.main import INJECT, app


@pytest.fixture()
def client():
    init_db()
    INJECT["latency_ms"] = 0
    INJECT["error_rate"] = 0.0
    mainmod._buckets.clear()
    mainmod.settings.API_KEY = ""
    mainmod.settings.RATE_LIMIT_RPS = 0
    mainmod.settings.CHAOS_ENABLED = True
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture()
def catalog(client):
    import app.db as dbmod
    s = dbmod.get_session()
    try:
        s.query(dbmod.Order).delete()
        s.query(dbmod.Product).delete()
        s.commit()
    finally:
        s.close()
    ids = {}
    for name, price, stock in (("book", 1000, 10), ("lamp", 2500, 3)):
        r = client.post("/api/products",
                        json={"name": name, "price_cents": price, "stock": stock})
        assert r.status_code == 201, r.text
        ids[name] = r.json()["id"]
    return ids


def test_products_crud(catalog, client):
    body = client.get("/api/products").json()
    assert {p["name"] for p in body["items"]} >= {"book", "lamp"}
    assert client.post("/api/products",
                       json={"name": "book", "price_cents": 1, "stock": 1}
                       ).status_code == 409
    book = next(p for p in body["items"] if p["name"] == "book")
    r = client.post(f"/api/products/{book['id']}/restock", json={"qty": 5})
    assert r.json()["stock"] == book["stock"] + 5
    assert client.post("/api/products/424242/restock",
                       json={"qty": 1}).status_code == 404


def test_order_with_product_promo_stock(catalog, client):
    book = catalog["book"]
    r = client.post("/api/orders",
                    json={"product_id": book, "qty": 2, "promo": "SAVE10"})
    assert r.status_code == 201, r.text
    assert r.json()["total_cents"] == 1800  # 1000*2*0.9
    stock = next(p for p in client.get("/api/products").json()["items"]
                 if p["id"] == book)["stock"]
    assert stock == 8
    assert client.post("/api/orders",
                       json={"product_id": book, "qty": 1, "promo": "NOPE"}
                       ).status_code == 422
    assert client.post("/api/orders",
                       json={"product_id": 424242, "qty": 1}).status_code == 404


def test_out_of_stock(catalog, client):
    lamp = catalog["lamp"]
    assert client.post("/api/orders",
                       json={"product_id": lamp, "qty": 99}).status_code == 409
    r = client.post("/api/orders", json={"product_id": lamp, "qty": 3})
    assert r.status_code == 201
    assert client.post("/api/orders",
                       json={"product_id": lamp, "qty": 1}).status_code == 409


def test_cancel_restores_stock(catalog, client):
    from app.worker import process_one
    book = catalog["book"]
    oid = client.post("/api/orders",
                      json={"product_id": book, "qty": 2}).json()["id"]
    assert client.post(f"/api/orders/{oid}/cancel").json()["status"] == "cancelled"
    # cancelled: worker skips, second cancel conflicts
    assert process_one(f'{{"order_id": {oid}}}') == "skipped"
    assert client.post(f"/api/orders/{oid}/cancel").status_code == 409
    stock = next(p for p in client.get("/api/products").json()["items"]
                 if p["id"] == book)["stock"]
    assert stock == 10
    # done orders cannot cancel
    oid2 = client.post("/api/orders",
                       json={"product_id": book, "qty": 1}).json()["id"]
    assert process_one(f'{{"order_id": {oid2}}}') == "ok"
    assert client.post(f"/api/orders/{oid2}/cancel").status_code == 409
    assert client.post("/api/orders/424242/cancel").status_code == 404


def test_stats_and_events(catalog, client):
    from app.worker import process_one
    oid = client.post("/api/orders",
                      json={"product_id": catalog["book"], "qty": 1}).json()["id"]
    assert process_one(f'{{"order_id": {oid}}}') == "ok"
    stats = client.get("/api/stats").json()
    assert stats["revenue_cents"] >= 1000
    assert stats["by_status"].get("done", 0) >= 1
    kinds = [e["kind"] for e in client.get("/api/events").json()["items"]]
    assert "order_created" in kinds
    assert client.get("/api/events?limit=200").json()["items"].__len__() <= 100
