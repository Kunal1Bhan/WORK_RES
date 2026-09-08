# Changelog

All notable changes, newest first. Format: `Added / Fixed / Changed / Security`.

## [Unreleased]

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
