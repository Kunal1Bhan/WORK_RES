# About — Infrastructure Reliability Lab

> Break things, watch them, measure them, fix them — with evidence for every claim.

## What
A self-contained distributed reliability platform: FastAPI API, background
worker, Postgres, Redis, Prometheus, Grafana — runnable locally, on Docker
Compose, or on Kubernetes (kind) — plus chaos injection, SLO measurement,
policy-driven remediation, traffic routing, DR drills, GPU scheduling with
model serving, and a Go Kubernetes operator. One-click desktop console
(`python lab_gui.py`) runs it all.

## Why
Reliability is learned by breaking systems under observation, not by reading
about it. Every milestone follows one rule — *implemented, tested, broken,
observed, measured, documented*.

## Who
DevOps/SRE learners and practitioners; interview-ready evidence of systems
thinking. Author: Kunal Bhan. License: MIT.

## Status
M0–M13 delivered and measured: API 194 RPS @ p95 34ms · pod-kill recovery on
kind in ~14s · RTX 3070 inference at 75 RPS · 38/38 tests green.
Evidence: [docs/PROJECT-REPORT.md](docs/PROJECT-REPORT.md).
Repo: https://github.com/Kunal1Bhan/WORK_RES
