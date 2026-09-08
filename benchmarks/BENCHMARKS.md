# Benchmarks (M10) — MEASURED 2026-09-08

## Environment
- Host: Windows, Python 3.13.11, uvicorn single worker (default)
- App: SQLite (`lab.db`), in-memory queue/cache, no worker running (queue not drained)
- CPU: (see ENVIRONMENT.md); GPU: NVIDIA RTX 3070 8GB (idle during API bench)
- Tool: `benchmarks/loadtest.py` (threads, 80% GET /health + 20% POST /api/orders)
- Target: local uvicorn on 127.0.0.1:8101

## Results

| Target RPS | Achieved RPS | Requests | Availability | p50 | p95 | p99 |
|---|---|---|---|---|---|---|
| 60 | 59.4 | 1191 | 100.0% | 16.6ms | 44.4ms | 64.6ms |
| 200 | 194.3 | 3920 | 100.0% | 14.8ms | 34.1ms | 48.7ms |

Raw logs: `benchmarks/results-60rps.jsonl`, `benchmarks/results-200rps.jsonl`
(re-runnable: `python benchmarks/loadtest.py --base http://127.0.0.1:8101 ...`).
SLO check: `python slo-engine/slo.py --log benchmarks/results-200rps.jsonl`
→ availability 100% PASS vs 99.9 target; p95 34ms well under 500ms SLO.

## Notes / limitations
- `localhost` (not `127.0.0.1`) adds a ~2s IPv6-fallback penalty per Python
  urllib connection on this host — always benchmark against 127.0.0.1 here.
- Single uvicorn worker, no Postgres/Redis in this run (compose/k8s numbers pending).
- DB replication lag: NOT MEASURED (needs Postgres primary/replica setup — M8).
- Saturation point not reached (194 rps clean); push higher RPS to find the knee.

## Model serving (M11) — MEASURED 2026-09-08
- Device: scheduler placed job on `cuda:0` (NVIDIA GeForce RTX 3070 Ti Laptop GPU,
  real `nvidia-smi` provider; sim fallback verified with `--provider sim`).
- Workload: 200 sequential POST /predict (bag-of-words sentiment, CPU inference).
- Before fix: per-request `nvidia-smi` spawn → 12 rps, p50 80ms.
- After fix (5s telemetry cache): **75 rps, p50 14.9ms, p99 29.1ms** (6x).
  Pure inference time 0.03ms — overhead is single-threaded HTTP + JSON.
- Limitation: no CUDA inference runtime (CPU weights); GPU telemetry is real,
  compute is CPU. Throughput via concurrent server pending.
