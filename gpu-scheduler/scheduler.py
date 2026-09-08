#!/usr/bin/env python3
"""scheduler.py — GPU inventory + job placement (M11).
Providers: nvidia-smi (real, parsed from XML) or sim (deterministic fake GPU).
Places a job on the GPU with most free memory; no GPUs -> CPU fallback.

Usage:
  python gpu-scheduler/scheduler.py inventory [--provider auto|nvidia|sim]
  python gpu-scheduler/scheduler.py place --mem-mb 2000
"""
import argparse
import json
import shutil
import subprocess
import xml.etree.ElementTree as ET


def nvidia_inventory():
    if shutil.which("nvidia-smi") is None:
        return None
    try:
        out = subprocess.run(["nvidia-smi", "-x", "-q"], capture_output=True,
                             text=True, timeout=15)
        if out.returncode != 0:
            return None
        root = ET.fromstring(out.stdout)
        gpus = []
        for i, g in enumerate(root.findall("gpu")):
            total = g.findtext("fb_memory_usage/total") or "0 MiB"
            used = g.findtext("fb_memory_usage/used") or "0 MiB"
            util = g.findtext("utilization/gpu_util") or "0 %"
            gpus.append({
                "id": i,
                "name": (g.findtext("product_name") or "unknown").strip(),
                "driver": (root.findtext("driver_version") or "").strip(),
                "mem_total_mb": int(total.split()[0]),
                "mem_used_mb": int(used.split()[0]),
                "util_pct": int(util.split()[0]),
                "provider": "nvidia-smi",
            })
        return gpus
    except Exception:
        return None


def sim_inventory():
    return [{"id": 0, "name": "SIM-GPU-8G", "driver": "sim",
             "mem_total_mb": 8192, "mem_used_mb": 1024,
             "util_pct": 12, "provider": "sim"}]


def inventory(provider="auto"):
    if provider in ("auto", "nvidia"):
        gpus = nvidia_inventory()
        if gpus:
            return gpus
        if provider == "nvidia":
            return []
    return sim_inventory()


def place(gpus, mem_mb):
    cands = [g for g in gpus
             if g["mem_total_mb"] - g["mem_used_mb"] >= mem_mb]
    if not cands:
        return {"device": "cpu", "reason": "no GPU with enough free memory"}
    best = max(cands, key=lambda g: g["mem_total_mb"] - g["mem_used_mb"])
    return {"device": f"cuda:{best['id']}", "gpu": best["name"],
            "provider": best["provider"]}


DEFAULT_API_PROVIDER = "auto"


def main(argv=None):
    # --provider accepted before or after the subcommand (cf. failurectl).
    after = argparse.ArgumentParser(add_help=False)
    after.add_argument("--provider", default=argparse.SUPPRESS,
                       choices=["auto", "nvidia", "sim"])
    p = argparse.ArgumentParser()
    p.add_argument("--provider", default=DEFAULT_API_PROVIDER,
                   choices=["auto", "nvidia", "sim"])
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("inventory", parents=[after])
    pl = sub.add_parser("place", parents=[after])
    pl.add_argument("--mem-mb", type=int, default=1000)
    a = p.parse_args(argv)
    gpus = inventory(a.provider)
    if a.cmd == "inventory":
        print(json.dumps(gpus, indent=2))
    else:
        print(json.dumps(place(gpus, a.mem_mb), indent=2))


if __name__ == "__main__":
    main()
