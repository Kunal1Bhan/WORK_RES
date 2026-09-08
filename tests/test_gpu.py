from scheduler import inventory, main as sched_main, place

from serve import gpu_telemetry, predict


def test_sim_inventory():
    gpus = inventory("sim")
    assert gpus[0]["mem_total_mb"] == 8192
    assert gpus[0]["provider"] == "sim"


def test_place_best_fit():
    gpus = [{"id": 0, "name": "a", "provider": "sim",
             "mem_total_mb": 8000, "mem_used_mb": 7000, "util_pct": 90},
            {"id": 1, "name": "b", "provider": "sim",
             "mem_total_mb": 8000, "mem_used_mb": 1000, "util_pct": 10}]
    assert place(gpus, 500)["device"] == "cuda:1"


def test_place_cpu_fallback():
    gpus = inventory("sim")
    r = place(gpus, 10 ** 9)
    assert r["device"] == "cpu"


def test_predict_labels():
    assert predict("I love this fast reliable service")[0] == "positive"
    assert predict("terrible broken crash down")[0] == "negative"


def test_gpu_telemetry_shape():
    t = gpu_telemetry()
    assert t["provider"] in ("nvidia-smi", "sim")
    assert t["mem_total_mb"] > 0


def test_provider_flag_both_positions(capsys):
    sched_main(["inventory", "--provider", "sim"])
    assert "SIM-GPU-8G" in capsys.readouterr().out
    sched_main(["--provider", "sim", "place", "--mem-mb", "100"])
    assert "cuda:0" in capsys.readouterr().out
