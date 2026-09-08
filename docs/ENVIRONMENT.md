# Environment Report (probed 2026-09-08, Windows host — CORRECTED)

Correction: an earlier revision wrongly stated "GPU NOT DETECTED".
`nvidia-smi` confirms a real GPU (table below).

| Item | Result |
|---|---|
| OS | Windows (win32) |
| Python | 3.13.11 |
| Docker | 29.1.2 client + daemon (Docker Desktop, running) |
| kubectl (client) | v1.34.1 |
| kind | v0.24.0 (`kind-lab` cluster, k8s v1.31.0 — verified working) |
| Go | 1.25.5 (user-local dist at `C:\Users\kunal\go\go-dist`, zip install, no admin) |
| GPU | **NVIDIA GeForce RTX 3070 Ti Laptop GPU**, 8GB, driver 610.62, CUDA 13.3 — REAL, used by M11 |
| pip-audit | 2.10.1 |
| winget | v1.29 (Go MSI install refused: UAC/exit 1602 in sandbox → zip fallback used) |

## Install-blocked (no admin in sandbox)
- Docker Windows service (`sc start` → access denied) — worked around by
  launching Docker Desktop as user.
- `kind`, `k3d`, `trivy`, Go MSI: not preinstalled. kind.exe + Go zip were
  fetched from official releases (network OK).

## Constraints
- kindnet CNI does NOT enforce NetworkPolicy — our policies apply cleanly but
  enforcement is NOT MEASURED (needs Calico).
- No cloud CLIs configured — multi-region stays simulated (M7 traffic router).
