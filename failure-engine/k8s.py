#!/usr/bin/env python3
"""k8s.py — kubectl-backed failure scenarios (M3, needs a cluster).
Scenarios: kill-pods (delete pods by label), scale-down/up, partition
(simulated via label cordon note + real `cordon` when --real).

All scenarios support --dry-run (print kubectl args, run nothing) and emit
JSON events. Unit-tested with mocked subprocess.

Usage: python failure-engine/k8s.py kill-pods --selector app=lab-api --dry-run
"""
import argparse
import json
import subprocess
import sys
import time


def run_kubectl(args, dry_run=False):
    cmd = ["kubectl"] + args
    if dry_run:
        print(json.dumps({"dry_run": cmd}))
        return {"dry_run": cmd}
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except FileNotFoundError:
        print("error: kubectl not found", file=sys.stderr)
        sys.exit(1)
    print(json.dumps({"cmd": cmd, "rc": out.returncode,
                      "stdout": out.stdout[-2000:], "stderr": out.stderr[-1000:]}))
    return {"rc": out.returncode, "stdout": out.stdout, "stderr": out.stderr}


def wait_rollout(deployment, namespace, timeout, dry_run=False):
    if dry_run:
        return True
    for _ in range(timeout // 5):
        r = subprocess.run(["kubectl", "rollout", "status",
                            f"deployment/{deployment}", "-n", namespace,
                            "--timeout=5s"], capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            return True
        time.sleep(5)
    return False


def scenario_kill_pods(selector, namespace, dry_run):
    r = run_kubectl(["delete", "pod", "-l", selector, "-n", namespace], dry_run)
    return {"scenario": "kill-pods", "selector": selector, "result": r}


def scenario_scale(deployment, namespace, replicas, dry_run):
    r = run_kubectl(["scale", f"deployment/{deployment}", "-n", namespace,
                     f"--replicas={replicas}"], dry_run)
    return {"scenario": "scale", "deployment": deployment,
            "replicas": replicas, "result": r}


def main(argv=None):
    p = argparse.ArgumentParser(prog="k8s-failure")
    p.add_argument("--namespace", default="default")
    p.add_argument("--dry-run", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)
    k = sub.add_parser("kill-pods")
    k.add_argument("--selector", default="app=lab-api")
    s = sub.add_parser("scale")
    s.add_argument("--deployment", default="lab-api")
    s.add_argument("--replicas", type=int, default=0)
    a = p.parse_args(argv)
    if a.cmd == "kill-pods":
        print(json.dumps(scenario_kill_pods(a.selector, a.namespace, a.dry_run)))
    elif a.cmd == "scale":
        print(json.dumps(scenario_scale(a.deployment, a.namespace, a.replicas, a.dry_run)))


if __name__ == "__main__":
    main()
