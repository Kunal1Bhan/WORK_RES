#!/usr/bin/env python3
"""seed.py — catalog + demo orders into a fresh database.
Usage: DATABASE_URL=... python scripts/seed.py [--items 5]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.db import Order, Product, get_session, init_db  # noqa: E402

CATALOG = [
    ("book", 1299, 50),
    ("lamp", 2499, 20),
    ("keyboard", 4999, 15),
    ("mug", 799, 100),
    ("cable", 499, 200),
    ("chair", 8999, 8),
    ("pen", 199, 500),
    ("desk", 14999, 5),
]


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--items", type=int, default=8)
    a = p.parse_args(argv)
    init_db()
    s = get_session()
    try:
        if s.query(Product).count() == 0:
            for name, price, stock in CATALOG:
                s.add(Product(name=name, price_cents=price, stock=stock))
            s.commit()
            print(f"seeded {len(CATALOG)} products")
        ids = []
        prods = s.query(Product).limit(a.items).all()
        for prod in prods:
            if prod.stock > 0:
                prod.stock -= 1
                row = Order(item=prod.name, status="pending",
                            product_id=prod.id, qty=1,
                            total_cents=prod.price_cents)
                s.add(row)
                s.flush()
                ids.append(row.id)
        s.commit()
    finally:
        s.close()
    print(f"seeded {len(ids)} orders: {ids}")


if __name__ == "__main__":
    main()
