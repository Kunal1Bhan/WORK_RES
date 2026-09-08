"""Pytest bootstrap: isolated sqlite DB + import path fixes.

Works regardless of whether pytest is launched from the lab dir or the repo root.
"""
import os
import sys

LAB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if LAB_DIR not in sys.path:
    sys.path.insert(0, LAB_DIR)
for p in ("slo-engine", "failure-engine", "remediation-engine"):
    full = os.path.join(LAB_DIR, p)
    if full not in sys.path:
        sys.path.append(full)

# Must be set before app.db is imported anywhere.
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(LAB_DIR, "test_lab.db")

from app.db import reset_engine, init_db  # noqa: E402

reset_engine()
init_db()
