"""Prometheus metrics shared by API + worker."""
from prometheus_client import Counter, Histogram, Gauge, CONTENT_TYPE_LATEST, generate_latest

REQUESTS = Counter("lab_http_requests_total", "Total HTTP requests", ["method", "path", "status"])
LATENCY = Histogram("lab_http_latency_seconds", "HTTP latency", ["path"])
ORDERS_CREATED = Counter("lab_orders_created_total", "Orders created")
ORDERS_PROCESSED = Counter("lab_orders_processed_total", "Orders processed", ["result"])
QUEUE_DEPTH = Gauge("lab_queue_depth", "Queue depth")
REVENUE_CENTS = Gauge("lab_revenue_cents", "Revenue from done orders (cents)")
LOW_STOCK = Gauge("lab_low_stock_products", "Products below stock threshold")
DB_UP = Gauge("lab_db_up", "DB reachable (1/0)")
CACHE_HITS = Counter("lab_cache_hits_total", "Cache hits")
CACHE_MISSES = Counter("lab_cache_misses_total", "Cache misses")


def metrics_payload():
    return generate_latest()


def metrics_content_type():
    return CONTENT_TYPE_LATEST
