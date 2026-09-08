# Security notes (M12)

## Dependency audit — MEASURED 2026-09-08 (`pip-audit -r requirements.txt`)
- Found 10 vulns → patched pytest 8.3.5→9.x and fastapi 0.115→0.118 (2 fixed).
- **Residual: 8 starlette 0.48.0 vulns** (URL path-confusion family, fixes need
  starlette ≥1.1). starlette 1.6.0 was tried and REVERTED: it breaks FastAPI
  0.118 (test collection error). Mitigation: upgrade FastAPI once it supports
  starlette 1.x; exploitability is limited (malformed request-target only
  affects pre-routing middleware/404 handlers; all our routes return 404 safely).
- `trivy` image scan: NOT AVAILABLE on host (documented gap).

## Hardening applied
- Dockerfile runs as non-root `lab` (uid 10001); `.dockerignore` shrinks context.
- `deploy/kubernetes/rbac.yaml`: least-privilege ServiceAccount/Role/RoleBinding
  (pods: get/list only); api deployment uses it.
- `deploy/kubernetes/networkpolicy.yaml`: default-deny + scoped allow rules.
  NOTE: kindnet does not enforce them — applied cleanly, enforcement NOT MEASURED.
- Chaos endpoints (`/chaos`) are dev-only hooks with validated inputs (422 on
  out-of-range); must sit behind auth before any shared-cluster use.
