# ADRs (initial)

## ADR-001 Python stack for M1
Context: need fastest reproducible M1. Options: Go / Python. Decision: Python (FastAPI+SQLAlchemy).
Trade-off: GIL limits worker throughput; acceptable for lab scale.

## ADR-002 Postgres with SQLite fallback
Context: reproducible without Docker. Decision: `DATABASE_URL` switch, Postgres in compose.
Failure implication: SQLite has no replication; DR demos require Postgres.

## ADR-003 Redis with in-memory fallback
Context: cache+queue without mandatory infra. Decision: `REDIS_URL` switch.
Failure implication: memory provider is in-process (no cross-replica sharing, data lost on restart).

## ADR-004 Prometheus + offline SLO evaluator
Context: need SLO evidence fast. Decision: `prometheus_client` + `slo.py` over JSONL.
Trade-off: no PromQL-based SLOs yet (M4-hardening).

## ADR-005 Chaos via app-level knobs first
Context: k8s chaos needs a cluster. Decision: `/chaos` endpoint + `failurectl` now, k8s faults in M3-hardening.
