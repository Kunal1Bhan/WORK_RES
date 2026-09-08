# 🧪 Infrastructure Reliability Lab

![CI](https://github.com/Kunal1Bhan/WORK_RES/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.13-blue)
![Go](https://img.shields.io/badge/go-1.25-cyan)
![Kubernetes](https://img.shields.io/badge/kubernetes-1.31-326ce5)
![License](https://img.shields.io/badge/license-MIT-green)

A hands-on distributed reliability platform in **Python + Go**: break things,
watch them, measure them, fix them — with evidence for every claim.

## 📖 About

**What it is:** a self-contained lab that runs a real distributed system
(FastAPI API, background worker, Postgres, Redis, Prometheus, Grafana) on your
machine or a local Kubernetes cluster — plus the tooling around it: chaos
injection, SLO measurement, policy-driven remediation, traffic routing, DR
drills, GPU scheduling with model serving, and a Go Kubernetes operator.

**Why it exists:** reliability is learned by breaking systems under observation,
not by reading about it. Every milestone here follows one rule — *implemented,
tested, broken, observed, measured, documented* — so each claim links to a test,
a benchmark number, or a captured incident (see
[docs/PROJECT-REPORT.md](docs/PROJECT-REPORT.md)).

**Who it's for:** DevOps/SRE learners and practitioners who want a single repo
that goes from `python lab_gui.py` to multi-service Kubernetes chaos drills,
and interview-ready evidence of systems thinking (find the full phase-by-phase
record in [docs/](docs/README.md)).

**Status:** all 13 milestones (M0–M13) delivered and measured — API 194 RPS @
p95 34ms, pod-kill recovery on kind, real RTX 3070 inference at 75 RPS.
Residual gaps are listed openly in the project report.

## ⚡ One-click start

**Double-click `Start Lab.bat`** — or run one command:

```
python lab_gui.py
```

That boots the API + worker (+ model serving) and opens the console:
service status lights, chaos injection, benchmarks+SLO, GPU/DR demos, live logs.

## 🗺️ Architecture

```mermaid
flowchart LR
    U([user / GUI]) --> API[FastAPI api]
    API --> DB[(Postgres / SQLite)]
    API --> C[(Redis / memory cache)]
    API --> Q[[Redis / memory queue]]
    Q --> W(worker)
    W --> DB
    API --> P([Prometheus])
    P --> G([Grafana])
    F[failurectl / k8s chaos] --> API
    S[slo.py] --> P
    R[policy remediate] --> API
    T[traffic router] --> API
    GPU{gpu scheduler} --> MS([model serving])
```

## 🧩 What's inside

| Area | Contents |
|---|---|
| `app/` | FastAPI API, worker, DB/cache/queue, metrics, OTEL tracing, JSON logs |
| `lab_gui.py` | One-click desktop console (stdlib only) |
| `failure-engine/` | `failurectl` CLI (latency/error/cpu) + kubectl scenarios |
| `slo-engine/` | SLO definitions + availability/p50/p95/p99 evaluator |
| `remediation-engine/` | Policy engine (cooldown, max-attempts, audit log) |
| `traffic-engine/` | Weighted router with health checks + failover |
| `dr-engine/` | DR drill runner with JSON reports |
| `gpu-scheduler/` + `model-serving/` | Real nvidia-smi placement + HTTP inference |
| `operator/` (Go) | ProductionService CRD + reconcile core (drift/scale/rollback) |
| `deploy/kubernetes/` | API, worker, Postgres, Redis, RBAC, NetworkPolicy |
| `observability/` | Prometheus rules, Grafana dashboard + datasource |
| `benchmarks/` | Load generator + measured report |
| `docs/` | [Full index](docs/README.md) — start with [PROJECT-REPORT](docs/PROJECT-REPORT.md) |

## 🚀 Quickstart (terminal)

```
pip install -r requirements.txt
uvicorn app.main:app --port 8000   # terminal 1
python -m app.worker               # terminal 2
pytest -q                          # 38 tests
```

Full stack: `docker compose up --build` (API :8000, Prometheus :9090, Grafana :3000).
Kubernetes: `make kind-up k8s-deploy` then `make k8s-chaos`.

## 📊 Measured highlights

- API: **194 RPS, p95 34ms, 100% availability** (`benchmarks/BENCHMARKS.md`)
- Pod-kill on kind: both API pods deleted → rescheduled in ~14s, traffic OK
- GPU inference (RTX 3070 Ti): **75 RPS, p50 15ms** after 6x telemetry-cache fix
- DR drill: PASS, 1034-row backup · Go operator: 5/5 tests

## 📄 License

MIT — see [LICENSE](LICENSE).
