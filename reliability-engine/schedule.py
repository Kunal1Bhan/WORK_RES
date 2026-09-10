#!/usr/bin/env python3
"""schedule.py — scheduled reliability runs (FR11).
Reads schedule.yaml ([{file, every_seconds}]), runs due experiments via
experiment.run_file, appends results to runs.jsonl. --once runs everything now.

Usage: python reliability-engine/schedule.py [--once] [--dir DIR]
"""
import argparse
import json
import os
import sys
import time

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "failure-engine"))
from experiment import run_file  # noqa: E402

STATE = os.path.join(HERE, ".schedule-state.json")
LOG = os.path.join(HERE, "runs.jsonl")


def load_schedule(path):
    with open(path) as f:
        return yaml.safe_load(f).get("jobs", [])


def load_state():
    try:
        with open(STATE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_state(s):
    with open(STATE, "w") as f:
        json.dump(s, f)


def log_run(entry):
    entry["ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def due_jobs(jobs, state, now, force=False):
    return [j for j in jobs
            if force or now - state.get(j["file"], 0) >= j.get("every_seconds", 3600)]


def run_once(schedule_path, api, directory, force=False):
    jobs = load_schedule(schedule_path)
    state = load_state()
    now = time.time()
    ran = []
    for job in due_jobs(jobs, state, now, force):
        path = job["file"] if os.path.isabs(job["file"]) else os.path.join(directory, job["file"])
        ok = run_file(path, api)
        state[job["file"]] = now
        ran.append(log_run({"job": job["file"], "passed": ok}))
    save_state(state)
    return ran


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--schedule", default=os.path.join(HERE, "schedule.yaml"))
    p.add_argument("--api", default="http://localhost:8000")
    p.add_argument("--dir", default=os.path.join(HERE, "..", "experiments"))
    p.add_argument("--once", action="store_true")
    p.add_argument("--loop-seconds", type=int, default=60)
    a = p.parse_args(argv)
    if a.once:
        print(json.dumps(run_once(a.schedule, a.api, a.dir, force=True), indent=2))
        return
    while True:
        try:
            run_once(a.schedule, a.api, a.dir)
        except Exception as e:
            print(f"scheduler error: {e}")
        time.sleep(a.loop_seconds)


if __name__ == "__main__":
    main()
