# Deployment

## Recommended architecture (today)

Single-host **Docker Compose**: `api` + `worker` + Postgres + Redis +
Prometheus + Grafana. Verified running 2026-09-08 (all 6 containers healthy,
smoke test green).

**Why:** the workload is small (measured headroom: 194 RPS on one uvicorn
worker), state fits in one Postgres, team size is one. Compose gives
healthchecks, restarts, volumes, and one-command rollback with near-zero ops
cost. Kubernetes manifests exist (`deploy/kubernetes/`) for the day traffic or
team size demands it — validated on kind, not used in this deployment.

## Process

```bash
cp .env.example .env        # set POSTGRES_PASSWORD (required), API_KEY, GRAFANA_PASSWORD
docker compose up -d --build
curl localhost:8000/ready   # {"db":"up",...}
```

Production toggles: `API_KEY=...` (gates /api/* + /chaos), `CHAOS_ENABLED=0`
(disables failure injection), `RATE_LIMIT_RPS=50`, `OTEL_ENABLED=1` + collector.

## Scaling
- API: `docker compose up -d --scale api=3` needs a load balancer in front
  (compose has none — use k8s manifests + Ingress instead beyond 1 host).
- Worker: `--scale worker=N` is safe (queue-competing consumers).

## Backups
- Postgres: `docker exec <db> pg_dump -U lab lab > backup.sql` (volume `pgdata`
  persists across restarts). Redis AOF enabled (`appendonly yes`, `cachedata`).
- No backups = cache/queue only (recomputable), DB dump is the one artifact.

## Rollback
`docker compose up -d --build` redeploys; rollback = `git checkout <prev> &&
docker compose up -d --build`. DB migrations are additive
(`CREATE INDEX IF NOT EXISTS`), safe both directions.

## Monitoring
- Prometheus :9090 (4 alert rules), Grafana :3000, API `/metrics`, `/live`, `/ready`.
- Alerts: 5xx>5% (page), p95>500ms, queue>50, db down (page).

## Cost
Single VPS/container host (~$6–12/mo class machine) + zero license cost.
Cloud alternative (managed PG + Redis + container service) ≈ $50–100/mo —
not justified at this scale.

## What this is NOT
Public-cloud deploy (AWS/GCP) was not performed: no cloud credentials/DNS in
this environment. Nothing here pretends otherwise — the compose + k8s configs
above are the deployment artifacts, validated locally.
