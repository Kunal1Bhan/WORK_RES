# Product Requirements Document (PRD)
Product Name: WORK_RES
Version: Draft v1.0
Owner: Kyōka (Kunal Bhan)

## 1. Product Overview
WORK_RES is a Resilience & Reliability Engineering Platform designed to help teams simulate failures, validate distributed systems, and benchmark ML workloads under stress. It combines Chaos Engineering, Observability, GPU Serving, and Kubernetes Operator automation into one cohesive product.

## 2. Goals & Objectives
- Provide a chaos experimentation framework for distributed systems.
- Enable SLO/SLA monitoring with real-time dashboards.
- Support GPU workloads with resilience testing.
- Automate reliability policies via a Go-based Kubernetes Operator.
- Deliver a scalable SaaS/Enterprise product with open-source adoption.

## 3. Target Users
- **Startups:** Validate reliability before scaling.
- **Enterprises:** Continuous resilience testing.
- **ML Teams:** Ensure GPU workloads survive failures.
- **DevOps/SREs:** Automate chaos experiments in CI/CD pipelines.

## 4. Scope
### In-Scope
- Chaos experiments (network, pod kill, resource exhaustion).
- Observability dashboards (latency, throughput, error rates).
- GPU workload reliability testing.
- Kubernetes Operator automation.
- Multi-cloud support (AWS, GCP, Azure).
- RBAC, audit logs, compliance reporting.

### Out-of-Scope (initial release)
- Non-Kubernetes environments.
- Proprietary monitoring stacks (focus on Prometheus/Grafana first).
- Advanced ML pipeline orchestration (future plugin ecosystem).

## 5. Features & Requirements
### 🔹 Chaos Engineering
- **FR1:** Predefined chaos scenarios.
- **FR2:** Custom experiment builder (YAML/JSON).
- **FR3:** Automated rollback validation.

### 🔹 Observability & SLOs
- **FR4:** Define SLOs (latency, error rate, throughput).
- **FR5:** Real-time dashboards with alerts.
- **FR6:** Historical benchmarking reports.

### 🔹 GPU Serving
- **FR7:** GPU resource scheduling.
- **FR8:** Fault injection for ML inference pipelines.
- **FR9:** Auto-scaling stress tests.

### 🔹 Operator Automation
- **FR10:** CRDs for chaos experiments.
- **FR11:** Scheduled reliability tests.
- **FR12:** Policy enforcement (e.g., survive 30% node loss).

### 🔹 Enterprise Features
- **FR13:** RBAC & team management.
- **FR14:** Audit logs & compliance reports.
- **FR15:** Plugin ecosystem for custom chaos modules.

## 6. Technical Architecture
- **Backend:** FastAPI (Python).
- **Frontend:** React/Next.js dashboard.
- **Data Layer:** Postgres/TimescaleDB for metrics storage.
- **Observability:** Prometheus + Grafana + OpenTelemetry.
- **Orchestration:** Kubernetes + Go Operator.
- **CI/CD:** GitHub Actions + ArgoCD.
- **Cloud Adapters:** AWS/GCP/Azure integration.

## 7. Roadmap
### Phase 1 – MVP (3–4 months)
FastAPI backend + React dashboard. Basic chaos scenarios. SLO monitoring.
GPU serving integration.
### Phase 2 – Beta (6–9 months)
Multi-cloud support. CI/CD integration. RBAC & audit logs. Operator automation.
### Phase 3 – Enterprise (12–18 months)
Plugin marketplace. Compliance-ready reporting. SLA-backed
Reliability-as-a-Service. Commercial support.

## 8. Success Metrics
- **Adoption:** GitHub stars, community contributions.
- **Reliability Impact:** % reduction in downtime post-chaos testing.
- **Performance:** GPU workloads benchmarked under stress.
- **Revenue:** SaaS subscriptions + enterprise licensing.

## 9. Risks & Mitigation
- **Risk:** Complexity of multi-cloud support.
  **Mitigation:** Start with AWS, expand later.
- **Risk:** Adoption barrier (chaos engineering is niche).
  **Mitigation:** Provide easy-to-use templates + CI/CD integration.
- **Risk:** Compliance requirements for enterprises.
  **Mitigation:** Build audit logs & reporting early.

---

## Appendix A — Implementation status in this repo (Sep 2026, verified)

| FR | Status in repo | Evidence |
|---|---|---|
| FR1 Predefined chaos | ✅ Done | `failurectl` (latency/error/cpu) + k8s kill-pods/scale, pod-kill recovery measured on kind |
| FR2 Custom builder | 🟡 Partial | `/chaos` hook + policies YAML; no YAML experiment-builder UI yet |
| FR3 Rollback validation | ✅ Done (app) | Go reconcile rollback + no-flap hold, `go test` 5/5; rollout rollback in k8s pending |
| FR4 SLO definitions | ✅ Done | `slos.yaml` ↔ Prometheus rules, test-wired |
| FR5 Dashboards + alerts | ✅ Done | Grafana dashboard, 4 alert rules, `/dashboard`, `/topology` deduction |
| FR6 Benchmark reports | ✅ Done | `BENCHMARKS.md` (measured RPS/latency) |
| FR7 GPU scheduling | ✅ Done (single host) | nvidia-smi placement on RTX 3070 Ti; no cluster scheduler |
| FR8 ML fault injection | 🟡 Partial | chaos knobs affect API; inference-pipeline faults not isolated |
| FR9 Autoscaling stress | 🟡 Partial | load generator to 194 RPS; no autoscaler |
| FR10 Chaos CRDs | 🟡 Partial | `ProductionService` CRD exists; chaos-specific CRDs pending |
| FR11 Scheduled tests | ❌ Roadmap | no scheduler/cron integration yet |
| FR12 Policy enforcement | 🟡 Partial | remediation policies with safeguards; no node-loss policies |
| FR13 RBAC/teams | 🟡 Partial | k8s RBAC + API-key gate; no team management |
| FR14 Audit/compliance | ✅ Done (audit) | `audit.log`, activity feed, drill reports; no compliance templates |
| FR15 Plugins | ❌ Roadmap | modular engines, no plugin loader yet |

**Architecture deltas vs §6:** frontend is tkinter + API-served pages (no
React — deliberate, zero-dep); metrics in Prometheus (no TimescaleDB); no
ArgoCD/multi-cloud (no cloud credentials). See `docs/PROJECT-REPORT.md` for
the honest gap list.
