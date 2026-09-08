# Milestones — status

| Milestone | Scope | Status |
|---|---|---|
| M0 Architecture | Phase 0 brief (15 items) | DONE (brief approved, this repo) |
| M1 Minimal Distributed System | API, Worker, DB, Cache, Queue | DONE (verified: pytest + live probes) |
| M2 Observability | Prometheus metrics, /metrics, queue-depth gauge | DONE (minimal; Grafana/OTEL pending) |
| M3 Failure Engine | failurectl latency/error/cpu/clear | DONE (minimal; k8s-aware scenarios pending) |
| M4 SLO Engine | availability + p50/p95/p99 + budget | DONE (offline log evaluator) |
| M5 Automated Remediation | chaos reset loop | DONE (minimal; policy engine pending) |
| M6 K8s Operator | ProductionService controller (Go) | NOT STARTED |
| M7 Multi-Cluster | two-region simulation | NOT STARTED |
| M8/M9 DR + drills | replication, promotion, drillctl | NOT STARTED |
| M10 Benchmarks | load scripts + report | NOT STARTED (sample log only) |
| M11 GPU serving | scheduler + model serving | NOT STARTED (no GPU detected → SIMULATED) |
| M12 Hardening | RBAC, TLS, image/secret scans | NOT STARTED |
| M13 Final Validation | full evidence review | NOT STARTED |

DoD per milestone: implemented + tested + broken (chaos) + observed + measured + documented.
