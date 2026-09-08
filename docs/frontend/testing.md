# Frontend Testing

Surfaces: tkinter console (`lab_gui.py`) + Swagger UI (`/docs`) + custom
dashboard (`/dashboard`). No display in CI/sandbox — tkinter `launch_gui`
cannot run headless, so it is covered indirectly.

## What runs where
| Test | Needs | Covers |
|---|---|---|
| `tests/test_gui.py` | nothing (stdlib http) | controller lifecycle |
| `tests/test_frontend_api.py` | TestClient | every UI-facing status: 200/201/404+envelope/405/422/500 |
| `tests/test_browser.py` | chromium+firefox, :8134 | docs flow, validation + chaos states in UI, mobile, a11y names/focus, weight budget |
| Manual | display | `python lab_gui.py` click-through (Dashboard→Chaos→Benchmark→Engines) |

## Budgets enforced in tests
- `/docs` HTML < 500 KB · mobile 390px zero horizontal overflow ·
  zero unnamed controls (one Swagger-owned exception documented in test).
