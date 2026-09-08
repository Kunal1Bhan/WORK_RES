from slo import evaluate, percentile


def test_percentile_empty():
    assert percentile([], 95) == 0.0


def test_percentile_known():
    assert percentile([1, 2, 3, 4], 50) == 2.5


def test_slo_pass():
    entries = [{"status": 200, "latency": 0.1}] * 999 + [{"status": 500, "latency": 1.0}]
    r = evaluate(entries, 99.9)
    assert r["verdict"] == "PASS"
    assert r["p50"] > 0
    assert r["total"] == 1000


def test_slo_fail():
    entries = [{"status": 500, "latency": 1.0}] * 50 + [{"status": 200, "latency": 0.1}] * 50
    r = evaluate(entries, 99.9)
    assert r["verdict"] == "FAIL"
    assert r["error_budget_remaining"] < 0


def test_slo_empty():
    r = evaluate([], 99.9)
    assert r["total"] == 0
    assert r["verdict"] == "FAIL"
