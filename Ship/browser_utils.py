from __future__ import annotations

import subprocess
from typing import Optional
import os
from playwright.async_api import async_playwright, Browser, BrowserContext


async def start_browser(headless: bool = True) -> tuple[Browser, BrowserContext, object]:
    try:
        p = await async_playwright().start()
        # Allow headful via env for debugging
        env_headful = os.environ.get("SHIP_HEADFUL") in {"1", "true", "TRUE"}
        launch_headless = headless and not env_headful
        browser = await p.chromium.launch(headless=launch_headless)
        context = await browser.new_context()
        return browser, context, p
    except Exception as e:
        # Attempt to install chromium runtime if missing
        try:
            subprocess.run(["python", "-m", "playwright", "install", "--with-deps", "chromium"], check=True)
            p = await async_playwright().start()
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context()
            return browser, context, p
        except Exception:
            raise e


