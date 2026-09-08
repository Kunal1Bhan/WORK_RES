# Infrastructure Reliability Lab (Python stack, M1 — Minimal Distributed System)

Simple DevOps project: FastAPI **API** + background **Worker** + **Postgres** (DB) +
**Redis** (cache + queue) + Prometheus metrics + `failurectl` chaos CLI + SLO calculator.

```
client -> API -> DB (postgres/sqlite) + cache (redis/memory) + queue (redis/memory) -> worker -> DB
              -> /metrics -> Prometheus
failurectl -> POST /chaos (latency / errors) ; slo.py computes availability + p50/p95/p99
```

## Quickstart (no Docker — uses sqlite + memory queue)
```
pip install -r requirements.txt
uvicorn app.main:app --port 8000   # terminal 1
python -m app.worker               # terminal 2
curl localhost:8000/health
curl -X POST localhost:8000/api/orders -H "Content-Type: application/json" -d "{\"item\":\"book\"}"
```

## Quickstart (full stack)
```
docker compose up --build
# api: :8000, prometheus: :9090
```

## Chaos + SLO + remediation
```
python failure-engine/failurectl.py error --rate 0.5   # --api URL works before or after the command
python failure-engine/failurectl.py clear
python remediation-engine/remediate.py
echo '{"status":200,"latency":0.1}' > req.jsonl
python slo-engine/slo.py --log req.jsonl --target 99.9
```

## K8s
```
kubectl apply -f deploy/kubernetes/api.yaml
```

## Tests
```
pytest -q
```
