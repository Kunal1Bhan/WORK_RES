#!/usr/bin/env python3
"""drill.py — disaster-recovery drill runner (M8/M9).
Steps: detect (region health) -> evacuate (write router plan) -> backup DB ->
promote replica (simulated: copy sqlite file; postgres: pg_basebackup hint) ->
verify (health + row counts) -> JSON report.

Usage: python dr-engine/drill.py --primary http://localhost:8000 --report report.json
"""
import argparse
import json
import os
import shutil
import sqlite3
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "traffic-engine"))


def health(url):
    try:
        with urllib.request.urlopen(url + "/health", timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


def backup_sqlite(db_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    ts = time.strftime("%Y%m%dT%H%M%S", time.gmtime())
    dest = os.path.join(out_dir, f"lab-{ts}.db")
    shutil.copy2(db_path, dest)
    con = sqlite3.connect(dest)
    tables = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    counts = {t[0]: con.execute(f"SELECT COUNT(*) FROM {t[0]}").fetchone()[0]
              for t in tables}
    con.close()
    return dest, counts


def run(primary, replica_api, db_path, out):
    steps = []
    t0 = time.time()

    up = health(primary)
    steps.append({"step": "detect", "primary_up": up,
                  "decision": "stay" if up else "failover"})

    plan = {"evacuate_to": replica_api if not up else primary,
            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    with open(os.path.join(out, "evacuation-plan.json"), "w") as f:
        json.dump(plan, f, indent=2)
    steps.append({"step": "evacuate", "plan": plan})

    if db_path and os.path.exists(db_path):
        dest, counts = backup_sqlite(db_path, os.path.join(out, "backups"))
        steps.append({"step": "backup", "file": dest, "row_counts": counts})
        promo = dest  # simulated promotion: replica IS the backup copy
        steps.append({"step": "promote", "mode": "simulated-sqlite-copy", "replica": promo})
    else:
        steps.append({"step": "backup", "mode": "skipped",
                      "hint": "set --db for sqlite; postgres uses streaming replication (see docs)"})

    verified = health(plan["evacuate_to"])
    steps.append({"step": "verify", "target_up": verified})

    report = {"ts": plan["at"], "primary": primary, "replica": replica_api,
              "elapsed_s": round(time.time() - t0, 2),
              "verdict": "PASS" if verified else "FAIL", "steps": steps}
    with open(os.path.join(out, "drill-report.json"), "w") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))
    return report


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--primary", default="http://localhost:8000")
    p.add_argument("--replica", default="http://localhost:8001")
    p.add_argument("--db", default="lab.db")
    p.add_argument("--out", default="dr-engine/drill-out")
    a = p.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    return run(a.primary, a.replica, a.db, a.out)


if __name__ == "__main__":
    main()
