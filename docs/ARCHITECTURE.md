# Architecture (M1 — Minimal Distributed System)

```
client -> API (FastAPI, 2 replicas on k8s; uvicorn locally)
            |-- DB: Postgres (compose/k8s) or SQLite fallback (local)
            |-- Cache: Redis or in-memory dict
            |-- Queue: Redis list or in-memory Queue -> Worker -> DB (marks orders done)
            \-- GET /metrics -> Prometheus (compose) ; alerts/SLOs in M2/M4
failurectl -> POST /chaos {latency_ms, error_rate}   (dev-only hook)
remediate.py -> POST /chaos {0, 0}                   (reset loop)
slo.py reads JSONL access logs -> availability, p50/p95/p99, error budget
```

Dependency graph: API -> {DB, Cache, Queue}; Worker -> {Queue, DB};
SLO Engine -> access logs; Failure Engine -> API `/chaos`; Remediation -> API `/chaos`.
Fallbacks are in-process only (no cross-replica sharing) — documented in ADR-002/003.
