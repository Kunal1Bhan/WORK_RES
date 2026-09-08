# Milestones — status (2026-09-08)

| Milestone | Scope | Status |
|---|---|---|
| M0 Architecture | Phase 0 brief (15 items) | DONE |
| M1 Minimal Distributed System | API, Worker, DB, Cache, Queue | DONE — deployed on kind (2 API + worker + postgres + redis, all Running); order E2E via real PG/Redis |
| M2 Observability | Metrics, logs, traces, alerts, Grafana | DONE — /metrics (50 series), JSON logs, OTEL (opt-in), 4 alert rules, Grafana dashboard+datasource in compose |
| M3 Failure Engine | failurectl + k8s scenarios | DONE — app-level chaos + kubectl kill-pods/scale (unit-tested); pod-kill recovery MEASURED on kind |
| M4 SLO Engine | SLO definitions + calculations | DONE — `slos.yaml` wired to alert rules (test-enforced); offline evaluator |
| M5 Automated Remediation | policy detector→remediation loops | DONE — policies.yaml + cooldown/max-attempt safeguards + audit log; 3 tests |
| M6 K8s Operator | ProductionService controller (Go) | DONE (core) — CRD + sample applied to kind; reconcile (drift/scale/rollback/no-flap) `go test` 5/5; full controller-runtime manager pending |
| M7 Multi-Cluster | traffic router + failover | DONE (simulated) — weighted router with health checks; no cloud, single kind cluster |
| M8/M9 DR + drills | replication, promotion, drillctl | DONE (simulated sqlite) — drill PASS, 1034-row backup measured; Postgres streaming replication pending |
| M10 Benchmarks | load scripts + report | DONE — 60rps: 59.4 achieved p95 44ms; 200rps: 194.3 achieved p95 34ms; BENCHMARKS.md |
| M11 GPU serving | scheduler + model serving | DONE — REAL RTX 3070 Ti via nvidia-smi; placement cuda:0; 75rps p50 15ms after telemetry-cache fix (6x) |
| M12 Hardening | RBAC, TLS, scans, backups | DONE (partial) — non-root, RBAC, NetworkPolicy, pip-audit (2 fixed, 8 residual documented); trivy/TLS pending |
| M13 Final Validation | evidence review | DONE — this file + PROJECT-REPORT.md |

DoD per milestone: implemented + tested + broken (chaos) + observed + measured + documented.
Residual gaps are listed in PROJECT-REPORT.md and tracked as follow-ups, not silent.
