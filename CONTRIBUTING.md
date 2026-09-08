# Contributing

## Ground rules
1. **Evidence-first.** Every claim cites a test, a benchmark number, or a
   captured run. Mark anything unmeasured as NOT MEASURED.
2. **Green before push:** `pytest -q` (38 tests) and `ruff check .` must pass.
   Go changes need `gofmt -l .` clean and `go test ./...` in `operator/`.
3. **Small, scoped commits** with conventional messages (`feat:`, `fix:`, `docs:`).

## Workflow
- Local dev needs nothing: SQLite + in-memory fallbacks (`uvicorn
  app.main:app`, `python -m app.worker`).
- Full stack: `docker compose up --build -d`. Kubernetes: `make kind-up k8s-deploy`.
- New engine? Add `engine-name/script.py` + `tests/test_<name>.py` + a row in
  this README's layout table and `docs/MILESTONES.md` if it moves a milestone.

## Security
Report vulnerabilities privately to the repo owner (see `SECURITY.md`).
