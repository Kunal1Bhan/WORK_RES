import k8s
from k8s import scenario_kill_pods, scenario_scale


def test_kill_pods_dry_run(capsys):
    r = scenario_kill_pods("app=lab-api", "default", dry_run=True)
    assert r["scenario"] == "kill-pods"
    assert r["result"]["dry_run"][0] == "kubectl"
    assert "delete" in r["result"]["dry_run"]


def test_scale_dry_run():
    r = scenario_scale("lab-api", "default", 0, dry_run=True)
    assert "--replicas=0" in r["result"]["dry_run"]


def test_k8s_cli_dry_run(capsys):
    k8s.main(["--dry-run", "kill-pods", "--selector", "app=x"])
    assert "kill-pods" in capsys.readouterr().out
