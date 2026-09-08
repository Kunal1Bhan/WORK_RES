# CHECKLIST — build phases (all complete, verified)

Every box links to evidence (tests, measured runs, or reports).

## Phase 0 — Architecture (M0)
- [x] 15-item brief: env report, requirements, architecture, dependency graph,
      failure model, threat model, tech ADRs, repo structure, roadmap, DoD,
      local/cloud strategy, testing + benchmarking strategy (`docs/`)

## Phase 1 — Workload (M1)
- [x] FastAPI API + worker + Postgres/SQLite + Redis/memory (`app/`)
- [x] Deployed on kind (2 API + worker + pg + redis Running), order E2E via PG/Redis
- [x] Docker image (non-root) + Compose stack + k8s manifests

## Phase 2 — Observability (M2)
- [x] Prometheus metrics (50 series), 4 alert rules, Grafana dashboard
- [x] JSON structured logs, opt-in OTEL tracing

## Phase 3 — Failure engine (M3)
- [x] `failurectl` (latency/error/cpu/clear) + kubectl kill-pods/scale
- [x] Pod-kill recovery measured on kind (~14s, traffic OK)

## Phase 4 — SLO engine (M4)
- [x] `slos.yaml` ↔ alert rules cross-tested; offline evaluator (avail + p50/p95/p99)

## Phase 5 — Remediation (M5)
- [x] Policy engine: cooldown, max-attempts, audit log

## Phase 6 — Operator (M6)
- [x] Go `ProductionService` CRD + reconcile core, `go test` 5/5, CRD applied to kind

## Phase 7 — Traffic (M7)
- [x] Weighted router + health checks + failover (simulated regions)

## Phase 8/9 — DR (M8/M9)
- [x] Drill runner: detect→evacuate→backup(1034 rows)→promote→verify, verdict PASS

## Phase 10 — Benchmarks (M10)
- [x] Load generator + BENCHMARKS.md (59 RPS p95 44ms; 194 RPS p95 34ms)

## Phase 11 — GPU (M11)
- [x] Real RTX 3070 Ti placement + model serving 75 RPS (6x telemetry-cache fix)

## Phase 12 — Hardening (M12)
- [x] RBAC, NetworkPolicy, pip-audit (2 fixed, 8 residual documented)

## Phase 13 — Validation (M13)
- [x] `docs/PROJECT-REPORT.md` gate verdicts

## Phase 14 — Productionization
- [x] Central config + `.env.example`, API-key auth, chaos kill-switch,
      rate limiting, security headers, request IDs, error envelopes, `/live`,
      pagination, 201+Location, PG pool + index migration, seed script
- [x] Real-process E2E + PG integration + CI services + docker build step
- [x] Compose deploy 6/6 healthy + smoke green; screenshots + real GIFs

## Phase 15 — Frontend
- [x] GUI thread-safety/lifecycle fixes; `/dashboard` UI; chromium+firefox E2E;
      responsive + a11y checks; frontend screenshots + demo GIF
- [x] 61/61 tests green, ruff clean
