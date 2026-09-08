import json
import os
import sqlite3

from drill import backup_sqlite, run


def test_backup_sqlite(tmp_path):
    db = str(tmp_path / "t.db")
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, item TEXT)")
    con.execute("INSERT INTO orders (item) VALUES ('book')")
    con.commit()
    con.close()
    dest, counts = backup_sqlite(db, str(tmp_path / "out"))
    assert os.path.exists(dest)
    assert counts == {"orders": 1}


def test_drill_failover_dead_primary(tmp_path):
    db = str(tmp_path / "t.db")
    sqlite3.connect(db).close()
    out = str(tmp_path / "drill")
    os.makedirs(out)
    report = run("http://127.0.0.1:9", "http://127.0.0.1:9", db, out)
    steps = {s["step"]: s for s in report["steps"]}
    assert steps["detect"]["decision"] == "failover"
    assert steps["backup"]["row_counts"] == {}
    assert report["verdict"] == "FAIL"  # nothing healthy to verify
    assert os.path.exists(os.path.join(out, "drill-report.json"))
    assert json.load(open(os.path.join(out, "drill-report.json")))["verdict"] == "FAIL"
