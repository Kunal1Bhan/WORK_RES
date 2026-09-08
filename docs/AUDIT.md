# Production Readiness Audit (2026-09-08)

Scope: FastAPI API + worker, Postgres/SQLite, Redis/memory, Compose, k8s
manifests, Go operator core, CI. Method: code inspection + live probing of the
running stack (API :8000, PG + Redis in Docker).

## Checklist

| # | Finding | Sev | Impact / Root cause → Fix | Status |
|---|---|---|---|---|
| 1 | No `.env.example`, env vars scattered across files | 🟠 High | Misconfig in prod → central `app/config.py` + `.env.example` | TODO |
| 2 | No authentication; `/chaos` reachable by anyone | 🔴 Critical | Anyone can inject failures → optional `API_KEY` gate + `CHAOS_ENABLED` kill-switch | TODO |
| 3 | No rate limiting | 🟠 High | Abuse/cascade → per-IP token bucket middleware | TODO |
| 4 | No security headers | 🟡 Medium | Clickjacking/MIME sniffing → headers middleware | TODO |
| 5 | Inconsistent error shapes; stack-trace risk | 🟠 High | Debug difficulty/leaks → envelope handlers (404/500), no trace to client | TODO |
| 6 | `/health` checks nothing; no `/live` vs `/ready` split | 🟡 Medium | K8s misprobes → `/live` (process) + `/ready` (deps), keep `/health` alias | TODO |
| 7 | No list endpoint/pagination; POST returns 200 not 201 | 🟡 Medium | API completeness → `GET /api/orders?limit&offset`, 201 + Location | TODO |
| 8 | Hardcoded DB password `lab/lab` in compose | 🟠 High | Secret in repo → `${POSTGRES_PASSWORD:?}` + `.env.example` | TODO |
| 9 | DB: no secondary indexes, no pool config, no seed story | 🟡 Medium | Slow filters, cold start → status index, pool env, `scripts/seed.py` | TODO |
| 10 | No E2E test against a real server process | 🟠 High | Regressions slip → `tests/test_e2e.py` (uvicorn+worker subprocesses) | TODO |
| 11 | No PG integration test in CI | 🟡 Medium | PG-only bugs slip → CI services + `tests/test_pg.py` (skip w/o PG) | TODO |
| 12 | GUI untested on headless CI (tkinter) | 🟢 Low | Only controller tested; `launch_gui` untested — accepted, documented | ACK |
| 13 | Starlette residual vulns (8, need 1.x) | 🟠 High | Auth-bypass-adjacent path bugs → documented; blocked by FastAPI 0.118 | KNOWN |
| 14 | Trivy unavailable; no image scan in CI | 🟡 Medium | Unknown image vulns → `pip-audit` in CI (done); trivy documented gap | PARTIAL |
| 15 | No request IDs / correlation | 🟢 Low | Traceability → `X-Request-ID` middleware | TODO |
| 16 | Compose missing resource limits, Grafana admin hardcoded | 🟢 Low | Noisy neighbor → limits + env password | TODO |

## Non-issues (checked, OK)
- SQL injection: SQLAlchemy ORM, no raw SQL except `SELECT 1`.
- Secrets in repo: none found (`grep` for password/key/token — only `lab/lab`
  dev default in compose, fixed by #8).
- Session handling: try/finally close everywhere; rollback on worker error.
- Graceful shutdown: worker handles SIGTERM/SIGINT; uvicorn handles SIGTERM.
- Non-root image, .dockerignore, HEALTHCHECK: present.
