"""Browser playtest: real mechanics + line-clear via debug hook + save flow."""
import os
import socket
import subprocess
import sys
import time
import urllib.request

import pytest

LAB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "http://127.0.0.1:8139"
ENV = dict(os.environ, DATABASE_URL="sqlite:///" + os.path.join(LAB, "e2e_game.db"))


def free():
    try:
        socket.create_connection(("127.0.0.1", 8139), timeout=1).close()
        return False
    except OSError:
        return True


playwright = pytest.importorskip("playwright.sync_api")


@pytest.fixture(scope="module")
def server():
    if not free():
        pytest.skip("port 8139 busy")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            pw.chromium.launch().close()
    except Exception as e:
        pytest.skip(f"no browsers: {e}")
    for f in ("e2e_game.db",):
        try:
            os.remove(os.path.join(LAB, f))
        except FileNotFoundError:
            pass
    api = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app",
                            "--host", "127.0.0.1", "--port", "8139"],
                           cwd=LAB, env=ENV, stdout=subprocess.DEVNULL,
                           stderr=subprocess.STDOUT)
    t0 = time.time()
    while time.time() - t0 < 40:
        try:
            if urllib.request.urlopen(BASE + "/health", timeout=3).status == 200:
                break
        except Exception:
            time.sleep(1)
    else:
        api.terminate()
        pytest.fail("API never became healthy")
    yield api
    api.terminate()
    api.wait(timeout=10)
    try:
        os.remove(os.path.join(LAB, "e2e_game.db"))
    except FileNotFoundError:
        pass


def test_line_clear_uses_real_code(server):
    """Set a near-full board through the debug hook, run the REAL clearLines,
    verify the row clears (mechanics unit-test against live game code)."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        p.goto(BASE + "/game?debug=1", wait_until="commit")
        p.wait_for_timeout(1200)
        p.keyboard.press("p")  # freeze gravity: setup must not race drops
        n = p.evaluate("""() => {
          const g = window.__game;
          const grid = g.grid;
          for (let x = 0; x < 10; x++) grid[19][x] = '#fff';
          grid[18][0] = '#fff';
          g.grid = grid;
          return g.clear();
        }""")
        assert n == 1
        # full row gone; the planted cell above correctly fell into row 19
        cells = p.evaluate(
          "window.__game.grid.flat().filter(Boolean).length")
        assert cells == 1
        b.close()


def test_play_save_and_leaderboard(server):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page(viewport={"width": 1100, "height": 800})
        errs = []
        p.on("pageerror", lambda e: errs.append(str(e)[:150]))
        p.goto(BASE + "/game", wait_until="commit")
        p.wait_for_timeout(1200)
        for _ in range(60):
            if p.locator("#overlay.open").count():
                break
            p.keyboard.press("Space")
            p.wait_for_timeout(100)
        assert p.locator("#overlay.open").count() == 1
        assert int(p.locator("#s-blocks").inner_text()) > 0
        p.fill("#op-name", "pytest")
        p.click("#save-score")
        p.wait_for_timeout(1200)
        assert "pytest" in p.locator("#scores").inner_text()
        assert errs == []
        b.close()
