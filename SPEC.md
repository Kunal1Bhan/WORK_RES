# SPEC — Infrastructure Reliability Lab (canonical technical reference)

## §1 Goal
A single repo that runs a real distributed system plus its reliability tooling
(workload, chaos, SLOs, remediation, routing, DR, GPU serving, operator),
provable phase by phase with tests and measurements. See `CHECKLIST.md` for
the build order and `docs/PROJECT-REPORT.md` for evidence.

## §2 Workload
- `POST /api/orders` → validate (1–200 chars) → Postgres row (`pending`) →
  Redis queue → worker marks `done`. Returns **201 + Location**.
- Shop orders: `product_id` + `qty` (+ optional promo `SAVE10`/`HALF`) →
  atomic stock decrement, discounted `total_cents`; 409 when out of stock,
  404 unknown product, 422 unknown promo. Cancel restores stock (pending only).
- Catalog: `products(id, name unique, price_cents, stock)` + restock endpoint;
  `stock_low` events below 5. Revenue = sum(done totals) via `/api/stats`.
- Activity feed: `events(kind, detail)` capped at 500 rows (orders, chaos,
  stock, products).
- `GET /api/orders?limit&offset` (capped), `GET /api/orders/{id}` (30s cache).
- Envelopes: `{"error":{"code","message"}}` for 401/403/404/422/429/500/503.
- Liveness `/live`, readiness `/ready` (DB SELECT 1 + queue depth), `/metrics`.

## §3 Configuration
`app/config.py` + `.env.example`. Keys: `DATABASE_URL`, `REDIS_URL`,
`POSTGRES_PASSWORD` (required in compose), `API_KEY` (gates `/api/*`, `/chaos`),
`CHAOS_ENABLED` (kill-switch), `RATE_LIMIT_RPS`/`_BURST`, `PAGE_SIZE_MAX`,
`POOL_SIZE`/`POOL_MAX_OVERFLOW`, `LOG_LEVEL`, `OTEL_ENABLED`.

## §4 Subsystems
- **Chaos** (`failure-engine/`): `/chaos` knobs (latency_ms ≥ 0, error_rate ∈
  [0,1]) + `failurectl` CLI + kubectl kill-pods/scale (dry-run supported).
- **SLO** (`slo-engine/`): `slos.yaml` targets ↔ Prometheus rules (test-wired);
  offline evaluator: availability, p50/p95/p99, error budget, PASS/FAIL.
- **Signals + situation** (`app/signals.py`, `GET /api/situation`): rolling
  5-min window (≤2000 samples) of status+latency → availability, p50/p95, RPS;
  live deduction vs SLOs (availability 99.9, p95 500ms, queue 50) with WARN on
  active chaos, recommendations, and a one-paragraph summary.
- **Remediation** (`remediation-engine/`): `policies.yaml`, first-match,
  cooldown + max-attempts safeguards, `audit.log`.
- **Traffic** (`traffic-engine/`): weighted router, health refresh, 502 all-down.
- **DR** (`dr-engine/`): detect → evacuate plan → backup → promote → verify,
  JSON report with verdict.
- **GPU** (`gpu-scheduler/` + `model-serving/`): nvidia-smi/sim providers,
  best-free-memory placement, HTTP sentiment inference with cached telemetry.
- **Operator** (`operator/`, Go): `ProductionService` CRD
  (`image`, `replicas`, `rollbackOnError`); pure `Reconcile(spec, actual)` →
  ordered actions (set-image/scale/rollback) + status; no-flap hold on
  recorded rollback.

## §5 Data
`orders(id PK, item ≤200, status, created_at)` + indexes on `status`,
`created_at` (additive `CREATE INDEX IF NOT EXISTS` migration in `init_db`).
Pool: size 5/overflow 10, `pool_pre_ping`. Seed: `scripts/seed.py`.

## §6 Frontends
- `lab_gui.py` (tkinter, stdlib): controller-owned subprocesses; all widget
  writes via UI queue; busy-states; background stop on close.
- `/dashboard` (single dependency-free HTML): live cards, order form, table,
  latency sparkline, chaos panel; XSS-escaped; responsive; ARIA labels.
- `/topology` (Packet-Tracer-style canvas): live-discovered nodes (API, worker,
  PG, Redis, Prometheus/Grafana/serving when reachable), RPS-driven packet
  animation (red under errors/chaos), click-to-inspect, and a deduction column
  rendering `/api/situation` (checks + recommendations + summary).
- `/game` (Block Ops): infra-themed falling-block game (7 services, bag,
  hold, ghost, levels, combos, sound); scores persisted (`scores` table) with
  leaderboard; per-game summary box + live lab situation line.
- `/docs` (Swagger, third-party).

## §7 Deployment
Single-host Compose (api/worker/pg/redis/prometheus/grafana) with healthchecks,
restarts, resource limits, volumes; k8s manifests (incl. RBAC, NetworkPolicy)
validated on kind. Ports: 8000/9090/3000.

## §8 Non-goals
No user accounts (API-key gate only), no multi-region cloud, no CUDA compute
(CPU inference + real telemetry), no controller-runtime manager (core only).
