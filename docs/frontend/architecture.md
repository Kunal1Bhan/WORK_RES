# Frontend Architecture & Audit

Scope note: this repo has **no web frontend codebase**. The user-facing
surfaces are (1) the tkinter desktop console (`lab_gui.py`, stdlib only) and
(2) FastAPI's auto-generated Swagger UI (`/docs`, third-party). No new
framework was introduced — that would rewrite working architecture without
cause.

## User journeys
```
Console: launch → Start all → lights green → chaos ⇄ clear → benchmark → engines → close
Swagger: /docs → expand op → Try it out → Execute → read status/response
```

## Audit findings
| # | Issue | Sev | Fix | Status |
|---|---|---|---|---|
| F1 | tkinter widgets written from worker threads (`show`, `eng_show`, `bench_go`) — intermittent crash/hang | 🔴 | Route all widget writes through `after`-pumped UI queue | TODO |
| F2 | `on_close` runs `stop_all` (blocking waits) on UI thread — freeze | 🟠 | Destroy window first, stop services in background | TODO |
| F3 | `refresh()` reschedules unconditionally; fires on dead root | 🟡 | `alive` guard + TclError catch | TODO |
| F4 | No busy-state: double-click benchmark runs two loadtests | 🟡 | Disable invoking button while running | TODO |
| F5 | Unknown-route 404 shape unverified (JSON envelope?) | 🟡 | Status-matrix tests | TODO |
| F6 | GUI can't be screenshotted/tested headless (no display in CI) | 🟢 | Controller covered; Swagger flows browser-tested; documented | ACCEPT |
| F7 | Single-browser evidence only (chromium) | 🟡 | Add Firefox run | TODO |

## Surfaces & contracts
- Console → API: `GET /health`, `POST /api/orders`, `POST /chaos`, scripts as
  subprocesses. All failures surface as text (never tracebacks).
- Browser → API: Swagger UI; expected codes 200/201/404/422/500 (+401/403/429
  when gates enabled).
