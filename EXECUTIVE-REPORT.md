# Executive Report — Infrastructure Reliability Lab (WORK_RES)

**Period:** 8–9 September 2026 · **16 commits** · **118 files** · **~3,600 lines**
· **73/73 tests green, ruff clean, `go test` 5/5**
**Repo:** https://github.com/Kunal1Bhan/WORK_RES

## How it was built
Evidence-first, in vertical slices: every feature was implemented, tested,
deliberately broken, measured, and documented before moving on. All
verification ran against real systems (local processes, Docker, a kind
Kubernetes cluster, a real RTX 3070 Ti, real Chromium/Firefox) — nothing
mocked, nothing fabricated. Every bug found was reproduced, root-caused,
fixed, and regression-tested.

## When and what

**8 Sep, evening — Foundation.** Scaffolded the Python M1 stack (FastAPI API +
worker + Postgres/SQLite + Redis/memory + Prometheus metrics + chaos CLI + SLO
evaluator) inside the system-design repo; fixed the startup/lifespan test
failure; moved it to its own repo **WORK_RES** and cleaned the old location.

**8 Sep, night — Full build-out (M1–M13).** Installed Go 1.25 (zip, no admin),
started Docker, created a real kind cluster (k8s v1.31). Deployed the stack,
killed pods and proved recovery (~14s), applied the Go operator CRD, measured
real benchmarks (194 RPS @ p95 34ms), ran model serving on the RTX 3070 Ti
(75 RPS after a 6x telemetry-cache fix), ran a passing DR drill — and fixed
real bugs found along the way (`psycopg` driver scheme, `:latest`
imagePullPolicy, argparse flag positions, per-request nvidia-smi cost,
`localhost` IPv6 benchmark penalty).

**8 Sep, late — Productionization.** Central env config + `.env.example`,
API-key auth, chaos kill-switch, per-IP rate limiting, security headers,
request IDs, error envelopes, `/live`, pagination, 201+Location, PG pool +
additive index migration, seed script, real-process E2E + PG integration
tests, CI with Postgres/Redis services + docker build, full Compose deploy
(6/6 healthy) with smoke test, Playwright screenshots + real demo GIF.
Fixed en route: worker Dockerfile HEALTHCHECK, Grafana provisioning YAML,
compose secrets, detached-instance 500s.

**8 Sep–9 Sep — Frontend & repo craft.** One-click tkinter console (then fixed
its thread-safety/lifecycle bugs), polished dark `/dashboard`, Packet-Tracer-
style `/topology` canvas with deduction column (`/api/situation`), kestrel-
style README + SPEC.md/CHECKLIST.md/PROMPT.md, monochrome architecture SVG,
community files (LICENSE, CONTRIBUTING, SECURITY, CHANGELOG, devcontainer,
dependabot, templates).

**9 Sep — Real usage + play.** Product catalog, promo codes, atomic inventory,
cancellations with stock restore, revenue + low-stock stats, activity feed;
then **Block Ops**, a full falling-block game (7-bag, hold, ghost, levels,
combos, sound, leaderboard, summary box), verified by playing it in a real
browser including a line-clear test against live game code.

## Current state
🟡 **Production Ready With Known Limitations** — deployable on a single host
with auth, limits, backups, rollback and monitoring. Open limitations (all
documented in-repo): no public-cloud deploy (no credentials), 8 residual
starlette findings (upgrade blocked by FastAPI 0.118), NetworkPolicy
unenforced on kindnet, tkinter needs a display.

## Run it
`bash scripts/demo.sh` · double-click `Start Lab.bat` · `python lab_gui.py` ·
`docker compose up --build -d` · `pytest -q` (73 tests)
