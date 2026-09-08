# Failure Model (M1 scope)

| Scenario | Detection | Effect | Recovery | Success signal |
|---|---|---|---|---|
| API pod crash | k8s liveness `/health` fails, `lab_http_requests_total` drops | 5xx spike, queue grows | k8s restarts pod; `remediate.py` clears chaos | `/ready` db=up, error rate back in SLO |
| Injected latency (`failurectl latency`) | p95/p99 rise in Prometheus | Slow responses, timeouts | `failurectl clear` / remediate | p95 back under target |
| Injected errors (`failurectl error`) | 5xx rate, availability < target | Failed orders | `failurectl clear` / remediate | `slo.py` verdict PASS |
| DB down | `/ready` db=down, `lab_db_up=0` | Order creation 500s | Restart postgres / compose | `/ready` db=up |
| Queue backlog | `lab_queue_depth` rising | Orders stuck `pending` | Scale workers | depth drains, orders `done` |

Measure every incident with: time-to-detect, time-to-healthy, error budget consumed (`slo.py`).
