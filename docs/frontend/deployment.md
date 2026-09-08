# Frontend Deployment & Troubleshooting

## Deployment model
- **Desktop console:** distributed as source — `Start Lab.bat` (or
  `python lab_gui.py`) on any machine with Python 3.12+. No build step, no
  bundler, no store. Stdlib-only GUI = zero GUI dependency risk.
- **Web surfaces** (`/docs`, `/dashboard`): served by the API itself —
  deployed wherever the API deploys (Compose/kind). No separate hosting,
  no CDN, no cloud needed. (No cloud credentials exist here; nothing to deploy to.)
- **Rollback:** `git checkout <prev>` — UI has no migrations or stored state.

## Troubleshooting
| Symptom | Cause → fix |
|---|---|
| GUI buttons do nothing | services not started — press ▶ Start all first |
| Dashboard shows DOWN | API not on :8000 — start it; check `/live` in browser |
| Order stuck `pending` | no worker draining — start worker (queue is per-process on memory backend) |
| Benchmark crawls on `localhost` | IPv6 fallback — use `127.0.0.1` |
| tkinter fails on Linux | needs python3-tk (`apt install python3-tk`) + a display |
| Fonts look off outside Windows | "Segoe UI" falls back to system font — cosmetic only |
