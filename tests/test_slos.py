import os
import yaml

LAB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _alerts():
    with open(os.path.join(LAB, "observability", "prometheus-rules.yml")) as f:
        rules = yaml.safe_load(f)
    return {r["alert"] for g in rules["groups"] for r in g["rules"]}


def test_slos_valid_and_wired():
    with open(os.path.join(LAB, "slo-engine", "slos.yaml")) as f:
        slos = yaml.safe_load(f)["slos"]
    assert len(slos) >= 4
    alerts = _alerts()
    for s in slos:
        assert s["target_pct"] >= 0 if "target_pct" in s else True
        if s["alert"] != "none":
            assert s["alert"] in alerts, f"{s['name']} alert missing in rules"


def test_rules_cover_slo_thresholds():
    with open(os.path.join(LAB, "observability", "prometheus-rules.yml")) as f:
        text = f.read()
    assert "0.05" in text and "lab_queue_depth > 50" in text and "lab_db_up == 0" in text
