# Changelog

All notable changes, newest first. Format: `Added / Fixed / Changed / Security`.

## [Unreleased]

## Block Ops game
- Added: `/game` — full falling-block game (7-bag, hold, ghost, levels,
  combos, sound, game-over flow), `scores` table + leaderboard API,
  `lab_games_played_total` metric, per-game summary box with lab situation.
- Verified: real browser playtests (mechanics, line-clear via debug hook,
  save→leaderboard), zero console errors.

## Packet-Tracer-style topology + deduction
- Added: rolling traffic signals + `GET /api/situation` (SLO verdicts,
  recommendations, summary); `/topology` canvas with live discovery,
  RPS-driven packet animation, click-to-inspect, deduction column.
- Fixed: first-paint blocked ~4–8s by sequential unbounded probes → parallel
  2s-timeout probes after the deduction paint (0.1s).

## Shop features (real usage, not a demo)
- Added: product catalog (create/list/restock), orders with product+qty+promo
  (SAVE10/HALF), atomic stock decrement, 409 out-of-stock, cancel with stock
  restore, revenue + low-stock stats, capped activity feed, revenue/low-stock
  metrics. Worker skips cancelled orders.
- Fixed: two detached-instance 500s (scalars captured pre-close) +
  `expire_on_commit=False`; PG migration transactions split per ALTER.
- Dashboard: shop grid with stock bars, revenue/low-stock cards, promo field,
  cancel buttons, activity feed. 66/66 tests green.

## 2026-09-08 — Productionization pass
- Added: `app/config.py` + `.env.example` (central env config), API-key auth,
  `CHAOS_ENABLED` kill-switch, per-IP rate limiting, security headers,
  request IDs, error envelopes, `/live`, paginated `GET /api/orders`, 201 +
  Location on create, request validation limits, PG pool config + status indexes
  with additive migration, `scripts/seed.py`.
- Added: real-process E2E (`tests/test_e2e.py`), PG integration
  (`tests/test_pg.py`), CI Postgres+Redis services + docker build step.
- Fixed: worker Dockerfile HEALTHCHECK (moved per-service; redis-ping for
  worker), Grafana provisioning YAML format, compose secrets via env,
  resource limits, Redis AOF persistence.
- Verified: full Compose deploy (6/6 healthy), smoke green, 48/48 tests,
  Playwright screenshots + real demo GIF.

## 2026-09-08 — M0–M13 complete + one-click console
- Added: `lab_gui.py` tkinter console + `Start Lab.bat` one-click launcher.
- Added: kind evidence (deploy, pod-kill recovery), Prometheus rules, Grafana
  dashboard, OTEL tracing, JSON logs, `slos.yaml`, policy remediation engine,
  traffic router, DR drill runner, GPU scheduler + model serving, Go operator
  (CRD + reconcile core), RBAC/NetworkPolicy, BENCHMARKS.md with measured numbers.
- Fixed: `postgresql+psycopg` driver scheme, `:latest` imagePullPolicy,
  failurectl/scheduler `--flag` argparse positions, per-request nvidia-smi cost
  (5s telemetry cache, 6x faster), localhost IPv6 benchmark penalty (use 127.0.0.1).
- Security: pytest/fastapi bumps via pip-audit; non-root image; 8 residual
  starlette vulns documented in `docs/SECURITY.md`.

## 2026-09-08 — M1 minimal stack
- Added: FastAPI API + worker, Postgres/SQLite, Redis/memory cache+queue,
  failurectl, slo.py, remediate reset loop, Compose, k8s API manifest, CI.
