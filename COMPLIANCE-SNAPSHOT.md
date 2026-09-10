# Compliance snapshot (2026-09-10T14:37:29Z)

| Control | Status | Detail |
|---|---|---|
| AUTH-01 api authentication enforceable | PASS | API_KEY unset (dev-open); teams file: none |
| CHAOS-01 chaos kill-switch available | PASS | CHAOS_ENABLED=1 |
| AUDIT-01 remediation audit log writable | PASS | remediation-engine/audit.log |
| BACKUP-01 db backups documented | PASS | see docs/deployment.md backup section |
| SCAN-01 dependency audit in CI | PASS | pip-audit step present |
| TEST-01 suite green | PASS | pytest -q |
