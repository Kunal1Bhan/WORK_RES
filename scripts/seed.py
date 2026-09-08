#!/usr/bin/env python3
"""seed.py — insert demo orders into a fresh database.
Usage: DATABASE_URL=... python scripts/seed.py [--items 5]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.db import Order, get_session, init_db  # noqa: E402

CATALOG = ["book", "lamp", "keyboard", "mug", "cable", "chair", "pen", "desk"]


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--items", type=int, default=8)
    a = p.parse_args(argv)
    init_db()
    s = get_session()
    try:
        ids = []
        for i in range(a.items):
            row = Order(item=CATALOG[i % len(CATALOG)], status="pending")
            s.add(row)
            s.flush()
            ids.append(row.id)
        s.commit()
    finally:
        s.close()
    print(f"seeded {len(ids)} orders: {ids}")


if __name__ == "__main__":
    main()
