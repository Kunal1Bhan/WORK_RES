#!/usr/bin/env python3
"""capture.py — real screenshots + demo GIF from the RUNNING stack.
Requires: compose stack up (api :8000, prometheus :9090, grafana :3000),
playwright chromium installed.

Usage: python docs/capture.py
Outputs: docs/screenshots/0*.png, docs/demo/application-demo.gif
"""
import os
import subprocess
import sys

LAB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOT = os.path.join(LAB, "docs", "screenshots")
DEMO = os.path.join(LAB, "docs", "demo")
os.makedirs(SHOT, exist_ok=True)
os.makedirs(DEMO, exist_ok=True)

from playwright.sync_api import sync_playwright  # noqa: E402


def shoot(page, name):
    path = os.path.join(SHOT, name)
    page.screenshot(path=path)
    print("shot:", path)


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto("http://127.0.0.1:8000/docs", wait_until="networkidle")
        page.wait_for_timeout(1500)
        shoot(page, "01-docs-home.png")

        # expand POST /api/orders
        page.click(".opblock-post .opblock-summary")
        page.wait_for_timeout(800)
        page.click(".opblock-post .try-out__btn")
        page.wait_for_timeout(500)
        ta = page.locator(".opblock-post textarea").first
        ta.fill('{\n  "item": "screenshot-book"\n}')
        page.click(".opblock-post .execute")
        page.wait_for_timeout(1500)
        shoot(page, "02-create-order.png")

        # expand + execute GET /api/orders
        page.click(".opblock-get .opblock-summary")
        page.wait_for_timeout(800)
        page.click(".opblock-get .try-out__btn")
        page.wait_for_timeout(500)
        page.click(".opblock-get .execute")
        page.wait_for_timeout(1500)
        shoot(page, "03-order-list.png")

        page.goto("http://127.0.0.1:9090/targets", wait_until="networkidle")
        page.wait_for_timeout(1200)
        shoot(page, "04-prometheus-targets.png")

        page.goto("http://127.0.0.1:3000/login", wait_until="networkidle")
        page.wait_for_timeout(1500)
        shoot(page, "05-grafana-login.png")
        browser.close()

        # GIF: record the same flow as video, then convert
        browser = pw.chromium.launch()
        ctx = browser.new_context(viewport={"width": 960, "height": 600},
                                  record_video_dir=DEMO, record_video_size={"width": 960, "height": 600})
        pg = ctx.new_page()
        pg.goto("http://127.0.0.1:8000/docs", wait_until="networkidle")
        pg.wait_for_timeout(800)
        pg.click(".opblock-post .opblock-summary")
        pg.wait_for_timeout(600)
        pg.click(".opblock-post .try-out__btn")
        pg.wait_for_timeout(400)
        pg.locator(".opblock-post textarea").first.fill('{\n  "item": "gif-book"\n}')
        pg.click(".opblock-post .execute")
        pg.wait_for_timeout(1500)
        pg.click(".opblock-get .opblock-summary")
        pg.wait_for_timeout(600)
        pg.click(".opblock-get .try-out__btn")
        pg.wait_for_timeout(400)
        pg.click(".opblock-get .execute")
        pg.wait_for_timeout(1500)
        video = pg.video.path()
        ctx.close()
        browser.close()

        import imageio_ffmpeg
        ff = imageio_ffmpeg.get_ffmpeg_exe()
        gif = os.path.join(DEMO, "application-demo.gif")
        subprocess.run([ff, "-y", "-i", video, "-vf", "fps=8,scale=800:-1",
                        gif], check=True, capture_output=True)
        os.remove(video)
        print("gif:", gif, os.path.getsize(gif) // 1024, "KB")


if __name__ == "__main__":
    sys.exit(main())
