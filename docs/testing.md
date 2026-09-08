# Testing

## Pyramid
- **Unit** (`tests/test_slo.py`, `test_failurectl.py`, `test_gpu.py`, …):
  pure logic — percentiles, arg parsing, placement, inference.
- **Integration** (`tests/test_api.py` via TestClient + lifespan,
  `tests/test_pg.py` against real Postgres when reachable, `test_remediation.py`,
  `test_router.py`, `test_drill.py`, `test_k8s.py`, `test_slos.py`):
  API+DB, policies, router, drill, k8s dry-run, SLO↔alert wiring.
- **E2E** (`tests/test_e2e.py`): real uvicorn + worker subprocesses, full
  journey create→done→chaos 500→recover→validate; needs Redis on :6379
  (CI provides it as a service), skipped otherwise.

## Run
```bash
pytest -q            # full suite (66 tests, ~25s; E2E spins subprocesses)
pytest tests/test_api.py -q
ruff check .         # lint
python -m pip_audit -r requirements.txt   # dependency audit
cd operator && go test ./...              # Go operator core
```

## CI (`.github/workflows/ci.yml`)
push/PR → pip install → ruff → pytest (with PG+Redis services) →
pip-audit (advisory) → `docker build`.
