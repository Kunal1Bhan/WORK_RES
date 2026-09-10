"""Plugin loader (FR15): drop a .py file in plugins/ exposing register().

A plugin module defines:
    def register():
        return {"name": "my-scenario",
                "run": lambda api, params: (ok_bool, detail_str)}
Loaded by failure-engine/experiment.py (action: plugin) without restarts.
"""
import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def load_plugins(directory=None):
    plugins = {}
    directory = directory or HERE
    for fname in sorted(os.listdir(directory)):
        if not fname.endswith(".py") or fname.startswith(("_", "test")):
            continue
        if fname == "__init__.py":
            continue
        path = os.path.join(directory, fname)
        mod_name = "lab_plugin_" + fname[:-3]
        try:
            spec = importlib.util.spec_from_file_location(mod_name, path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            info = mod.register()
            plugins[info["name"]] = info["run"]
        except Exception as e:
            plugins[fname] = ("load_error", str(e))
    return plugins
