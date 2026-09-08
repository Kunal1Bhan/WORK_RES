"""Controller tests: real subprocess lifecycle with a dummy HTTP service."""

import pytest

from lab_gui import LabController

PORT = 8231


@pytest.fixture()
def ctl():
    cmd = ["python", "-m", "http.server", str(PORT)]
    services = {"dummy": {"cmd": cmd,
                          "health": f"http://127.0.0.1:{PORT}/",
                          "links": {}}}
    c = LabController(services=services)
    yield c
    c.stop_all()


def test_start_stop_lifecycle(ctl):
    assert ctl.status() == {"dummy": "DOWN"}
    assert ctl.start("dummy") == "started"
    assert ctl.is_up("dummy")
    assert ctl.start("dummy") == "already running"
    assert ctl.stop("dummy") == "stopped"
    assert not ctl.is_up("dummy")
    assert ctl.stop("dummy") == "not running"


def test_start_all_stop_all(ctl):
    assert ctl.start_all() == {"dummy": "started"}
    assert ctl.status() == {"dummy": "UP"}
    assert ctl.stop_all() == {"dummy": "stopped"}


def test_unhealthy_service_times_out_fast():
    c = LabController(services={"ghost": {
        "cmd": ["python", "-c", "import time; time.sleep(300)"],
        "health": "http://127.0.0.1:9/", "links": {}}})
    try:
        # health never comes up; start() waits then reports unhealthy
        assert c.start("ghost", timeout_s=2) == "unhealthy"
        assert not c.is_up("ghost")
    finally:
        c.stop_all()
