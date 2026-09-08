#!/usr/bin/env python3
"""Infrastructure Reliability Lab — one-click desktop console.

Run:  python lab_gui.py        (or double-click Start Lab.bat)
Starts the API + worker (+ optional model serving), then shows a GUI with
service status, chaos injection, benchmarks/SLO, engine demos and logs.

Only stdlib is used (tkinter). Business logic lives in LabController so it
is unit-testable without a display (see tests/test_gui.py).
"""
import json
import os
import queue
import subprocess
import sys
import threading
import time
import urllib.request

LAB_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, LAB_DIR)

SERVICES = {
    "api": {
        "cmd": [sys.executable, "-m", "uvicorn", "app.main:app",
                "--host", "127.0.0.1", "--port", "8000"],
        "health": "http://127.0.0.1:8000/health",
        "links": {"API docs": "http://127.0.0.1:8000/docs",
                  "Metrics": "http://127.0.0.1:8000/metrics"},
    },
    "worker": {
        "cmd": [sys.executable, "-m", "app.worker"],
        "health": None,  # background process: alive == healthy
        "links": {},
    },
    "model-serving": {
        "cmd": [sys.executable, "model-serving/serve.py", "--port", "8100"],
        "health": "http://127.0.0.1:8100/health",
        "links": {"Predict demo": "http://127.0.0.1:8100/metrics"},
        "optional": True,
    },
}


def http_json(url, timeout=4):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.status, r.read().decode()


def http_post_json(url, body, timeout=5):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode()


def _call(desc, fn):
    """Run fn(); distinguish server-responded errors from unreachable."""
    import urllib.error
    try:
        code, text = fn()
        out = f"{desc} -> {code} {text}"
        return out
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:500]
        return f"{desc} -> server responded {e.code}: {body}"
    except Exception as e:
        return f"{desc} -> error: service not reachable ({e}). Start services first."


class LabController:
    """Owns service subprocesses and one-shot engine runs."""

    def __init__(self, services=None, lab_dir=LAB_DIR):
        self.services = services or SERVICES
        self.lab_dir = lab_dir
        self.procs = {}
        self.log_q = queue.Queue()

    def log(self, msg):
        self.log_q.put(f"[{time.strftime('%H:%M:%S')}] {msg}")

    # ---- services ----
    def is_up(self, name):
        p = self.procs.get(name)
        if p is None or p.poll() is not None:
            return False
        url = self.services[name].get("health")
        if not url:
            return True
        try:
            return http_json(url)[0] == 200
        except Exception:
            return False

    def start(self, name, timeout_s=20.0):
        if self.is_up(name):
            return "already running"
        spec = self.services[name]
        self.log(f"starting {name}: {' '.join(spec['cmd'])}")
        self.procs[name] = subprocess.Popen(
            spec["cmd"], cwd=self.lab_dir,
            stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        deadline = time.time() + timeout_s
        while time.time() < deadline:  # wait for health
            if self.is_up(name):
                self.log(f"{name} is up")
                return "started"
            time.sleep(0.5)
        self.log(f"{name} did not become healthy (still running in background)")
        return "unhealthy"

    def stop(self, name):
        p = self.procs.pop(name, None)
        if p is None:
            return "not running"
        p.terminate()
        try:
            p.wait(timeout=8)
        except subprocess.TimeoutExpired:
            p.kill()
        self.log(f"{name} stopped")
        return "stopped"

    def start_all(self, include_optional=True):
        out = {}
        for name, spec in self.services.items():
            if spec.get("optional") and not include_optional:
                continue
            out[name] = self.start(name)
        return out

    def stop_all(self):
        return {n: self.stop(n) for n in list(self.procs)}

    def status(self):
        return {n: ("UP" if self.is_up(n) else "DOWN") for n in self.services}

    # ---- one-shot actions (each returns printable text) ----
    def run_script(self, argv, timeout=300):
        self.log("$ python " + " ".join(argv))
        try:
            out = subprocess.run([sys.executable] + argv, cwd=self.lab_dir,
                                 capture_output=True, text=True, timeout=timeout)
            text = (out.stdout + out.stderr).strip() or "(no output)"
            self.log(text[-2000:])
            return text
        except subprocess.TimeoutExpired:
            return "error: timed out"

    def chaos(self, kind, value=None):
        body = {"latency_ms": 0, "error_rate": 0.0}
        if kind == "latency":
            body["latency_ms"] = int(value or 500)
        elif kind == "error":
            body["error_rate"] = float(value or 0.5)
        out = _call(f"chaos {kind}",
                    lambda: http_post_json("http://127.0.0.1:8000/chaos", body))
        self.log(out)
        return out

    def quick_order(self):
        out = _call("order", lambda: http_post_json(
            "http://127.0.0.1:8000/api/orders", {"item": "gui-book"}))
        self.log(out)
        return out

    def quick_predict(self, text="I love this fast reliable service"):
        out = _call("predict", lambda: http_post_json(
            "http://127.0.0.1:8100/predict", {"text": text}))
        self.log(out)
        return out


def launch_gui(controller=None):
    import tkinter as tk
    from tkinter import ttk
    import webbrowser

    ctl = controller or LabController()
    root = tk.Tk()
    root.title("Infrastructure Reliability Lab")
    root.geometry("860x620")

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True, padx=8, pady=8)

    # ---- Dashboard tab ----
    dash = ttk.Frame(notebook)
    notebook.add(dash, text="Dashboard")
    lights = {}
    row = 0
    ttk.Label(dash, text="Services", font=("Segoe UI", 12, "bold")).grid(
        row=row, column=0, sticky="w", pady=4)
    row += 1
    for name in ctl.services:
        dot = tk.Label(dash, text="●", fg="grey", font=("Segoe UI", 16))
        dot.grid(row=row, column=0)
        ttk.Label(dash, text=name, font=("Segoe UI", 11)).grid(
            row=row, column=1, sticky="w")
        lights[name] = dot
        row += 1

    def refresh():
        for name, dot in lights.items():
            up = ctl.is_up(name)
            dot.config(fg="green" if up else "red")
        root.after(2000, refresh)

    btns = ttk.Frame(dash)
    btns.grid(row=row, column=0, columnspan=3, pady=10)
    ttk.Button(btns, text="▶ Start all",
               command=lambda: threading.Thread(
                   target=ctl.start_all, daemon=True).start()).pack(side="left", padx=4)
    ttk.Button(btns, text="■ Stop all",
               command=ctl.stop_all).pack(side="left", padx=4)
    ttk.Button(btns, text="Send test order",
               command=lambda: threading.Thread(
                   target=ctl.quick_order, daemon=True).start()).pack(side="left", padx=4)
    linkrow = ttk.Frame(dash)
    linkrow.grid(row=row + 1, column=0, columnspan=3, pady=4)
    for name, spec in ctl.services.items():
        for label, url in spec.get("links", {}).items():
            ttk.Button(linkrow, text=label,
                       command=lambda u=url: webbrowser.open(u)).pack(side="left", padx=4)

    # ---- Chaos tab ----
    chaos = ttk.Frame(notebook)
    notebook.add(chaos, text="Chaos")
    out_chaos = tk.Text(chaos, height=8)
    out_chaos.pack(fill="x", padx=8, pady=8)

    def show(fn):
        def go():
            out_chaos.delete("1.0", "end")
            out_chaos.insert("end", fn() + "\n")
        threading.Thread(target=go, daemon=True).start()

    fr = ttk.Frame(chaos)
    fr.pack(pady=4)
    ttk.Button(fr, text="Inject latency 500ms",
               command=lambda: show(lambda: ctl.chaos("latency", 500))).pack(side="left", padx=4)
    ttk.Button(fr, text="Inject 50% errors",
               command=lambda: show(lambda: ctl.chaos("error", 0.5))).pack(side="left", padx=4)
    ttk.Button(fr, text="CPU burn (local)",
               command=lambda: show(lambda: ctl.run_script(
                   ["failure-engine/failurectl.py", "cpu", "--seconds", "3"]))).pack(side="left", padx=4)
    ttk.Button(fr, text="Clear chaos",
               command=lambda: show(lambda: ctl.chaos("clear"))).pack(side="left", padx=4)

    # ---- Benchmark tab ----
    bench = ttk.Frame(notebook)
    notebook.add(bench, text="Benchmark")
    out_bench = tk.Text(bench, height=14)
    out_bench.pack(fill="both", expand=True, padx=8, pady=8)
    fr2 = ttk.Frame(bench)
    fr2.pack(pady=4)

    def bench_go():
        out_bench.delete("1.0", "end")
        out_bench.insert("end", "running load test…\n")
        txt = ctl.run_script(["benchmarks/loadtest.py", "--base", "http://127.0.0.1:8000",
                              "--rps", "60", "--seconds", "15",
                              "--out", "benchmarks/results-gui.jsonl"])
        out_bench.insert("end", txt + "\n")
        slo = ctl.run_script(["slo-engine/slo.py", "--log",
                              "benchmarks/results-gui.jsonl", "--target", "99.9"])
        out_bench.insert("end", "SLO:\n" + slo + "\n")

    ttk.Button(fr2, text="Run 60 RPS benchmark + SLO",
               command=lambda: threading.Thread(target=bench_go, daemon=True).start()).pack(padx=4)

    # ---- Engines tab ----
    eng = ttk.Frame(notebook)
    notebook.add(eng, text="Engines")
    out_eng = tk.Text(eng, height=14)
    out_eng.pack(fill="both", expand=True, padx=8, pady=8)
    fr3 = ttk.Frame(eng)
    fr3.pack(pady=4)

    def eng_show(fn):
        def go():
            out_eng.delete("1.0", "end")
            out_eng.insert("end", fn() + "\n")
        threading.Thread(target=go, daemon=True).start()

    ttk.Button(fr3, text="GPU inventory",
               command=lambda: eng_show(lambda: ctl.run_script(
                   ["gpu-scheduler/scheduler.py", "inventory"]))).pack(side="left", padx=4)
    ttk.Button(fr3, text="Predict demo",
               command=lambda: eng_show(ctl.quick_predict)).pack(side="left", padx=4)
    ttk.Button(fr3, text="DR drill",
               command=lambda: eng_show(lambda: ctl.run_script(
                   ["dr-engine/drill.py", "--primary", "http://127.0.0.1:8000",
                    "--replica", "http://127.0.0.1:8100", "--db", "lab.db",
                    "--out", "dr-engine/drill-out-gui"]))).pack(side="left", padx=4)
    ttk.Button(fr3, text="Remediate (dry-run)",
               command=lambda: eng_show(lambda: ctl.run_script(
                   ["remediation-engine/remediate.py", "--dry-run", "--once"]))).pack(side="left", padx=4)

    # ---- Log pane ----
    logbox = tk.Text(root, height=8, bg="#111", fg="#0f0")
    logbox.pack(fill="x", padx=8, pady=(0, 8))

    def pump():
        while True:
            try:
                line = ctl.log_q.get_nowait()
            except queue.Empty:
                break
            logbox.insert("end", line + "\n")
            logbox.see("end")
        root.after(300, pump)

    def on_close():
        ctl.stop_all()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    ctl.log("console ready — press ▶ Start all")
    refresh()
    pump()
    root.mainloop()


if __name__ == "__main__":
    launch_gui()
