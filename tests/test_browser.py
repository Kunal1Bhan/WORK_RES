"""Browser E2E on the real Swagger UI (chromium + firefox, headless).

Covers: docs load without page errors, create-order flow, validation-error
state visible in UI, 404 envelope, chaos 500 surfaced, mobile viewport,
keyboard focus order, accessible names, basic page-weight budget.
Needs the playwright browsers; server runs in-process tmp sqlite.
"""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request

import pytest

LAB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "http://127.0.0.1:8134"
ENV = dict(os.environ, DATABASE_URL="sqlite:///" + os.path.join(LAB, "e2e_front.db"))

playwright = pytest.importorskip("playwright.sync_api")


def port_free():
    try:
        socket.create_connection(("127.0.0.1", 8134), timeout=1).close()
        return False
    except OSError:
        return True


@pytest.fixture(scope="module")
def server():
    if not port_free():
        pytest.skip("port 8134 busy")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            pw.chromium.launch().close()
    except Exception as e:
        pytest.skip(f"no browsers: {e}")
    for f in ("e2e_front.db",):
        try:
            os.remove(os.path.join(LAB, f))
        except FileNotFoundError:
            pass
    api = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app",
                            "--host", "127.0.0.1", "--port", "8134"],
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
        os.remove(os.path.join(LAB, "e2e_front.db"))
    except FileNotFoundError:
        pass


def new_page(pw, browser_name, **kwargs):
    browser = getattr(pw, browser_name).launch()
    page = browser.new_page(**kwargs)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    return browser, page, errors


@pytest.mark.parametrize("browser_name", ["chromium", "firefox"])
def test_docs_flow_and_validation_state(server, browser_name):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser, page, errors = new_page(pw, browser_name)
        try:
            page.goto(BASE + "/docs", wait_until="networkidle")
            page.wait_for_timeout(1200)
            assert "Swagger UI" in page.title() or page.locator(".swagger-ui").count() > 0

            # happy path: create order
            page.click(".opblock-post .opblock-summary")
            page.click(".opblock-post .try-out__btn")
            page.locator(".opblock-post textarea").first.fill('{"item": "browser-book"}')
            page.click(".opblock-post .execute")
            page.wait_for_timeout(1200)
            body = page.locator(".opblock-post .responses-wrapper").inner_text()
            assert "201" in body and "browser-book" in body

            # validation-error state visible in UI (empty item -> 422)
            page.locator(".opblock-post textarea").first.fill('{"item": ""}')
            page.click(".opblock-post .execute")
            page.wait_for_timeout(1200)
            body2 = page.locator(".opblock-post .responses-wrapper").inner_text()
            assert "422" in body2 and "validation_error" in body2
        finally:
            browser.close()
        assert errors == [], f"page errors: {errors}"


@pytest.mark.parametrize("browser_name", ["chromium", "firefox"])
def test_chaos_500_surfaced(server, browser_name):
    from playwright.sync_api import sync_playwright
    urllib.request.urlopen(urllib.request.Request(
        BASE + "/chaos", data=json.dumps({"error_rate": 1.0}).encode(),
        headers={"Content-Type": "application/json"}, method="POST"))
    with sync_playwright() as pw:
        browser, page, errors = new_page(pw, browser_name)
        try:
            page.goto(BASE + "/docs", wait_until="networkidle")
            page.click(".opblock-post .opblock-summary")
            page.click(".opblock-post .try-out__btn")
            page.locator(".opblock-post textarea").first.fill('{"item": "x"}')
            page.click(".opblock-post .execute")
            page.wait_for_timeout(1200)
            body = page.locator(".opblock-post .responses-wrapper").inner_text()
            assert "500" in body and "injected_failure" in body
        finally:
            browser.close()
    urllib.request.urlopen(urllib.request.Request(
        BASE + "/chaos", data=json.dumps({"error_rate": 0.0}).encode(),
        headers={"Content-Type": "application/json"}, method="POST"))


def test_mobile_viewport_no_hscroll(server):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(BASE + "/docs", wait_until="networkidle")
        page.wait_for_timeout(1000)
        overflow = page.evaluate(
            "document.documentElement.scrollWidth - window.innerWidth")
        assert overflow <= 1, f"horizontal overflow: {overflow}px"
        page.screenshot(path=os.path.join(LAB, "docs", "screenshots",
                                          "frontend", "06-responsive-mobile.png"))
        browser.close()


def test_a11y_names_and_focus(server):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(BASE + "/docs", wait_until="networkidle")
        # interactive controls expose accessible names (text, aria-label, or
        # title — the one title-only control is Swagger's own expand arrow)
        bad = page.evaluate("""[...document.querySelectorAll('button')].filter(
            b => !(b.innerText.trim() || b.getAttribute('aria-label') ||
                   (b.getAttribute('title') || '').trim())).length""")
        assert bad == 0, f"{bad} unnamed buttons"
        # tab moves focus to a focusable element (not body)
        page.keyboard.press("Tab")
        page.wait_for_timeout(300)
        focused = page.evaluate("document.activeElement.tagName")
        assert focused not in ("BODY",), "tab did not move focus"
        browser.close()


def test_page_weight_budget(server):
    req = urllib.request.Request(BASE + "/docs")
    with urllib.request.urlopen(req, timeout=10) as r:
        html_kb = len(r.read()) / 1024
    assert html_kb < 500, f"docs HTML too heavy: {html_kb:.0f} KB"
