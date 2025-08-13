from __future__ import annotations

import asyncio
from pathlib import Path

from playwright.async_api import Page

from .config import load_app_config, ensure_data_dirs
from .browser_utils import start_browser


async def main() -> None:
    config = load_app_config()
    ensure_data_dirs(config.data_dir)

    # Headful mode for manual login
    browser, context, p = await start_browser(headless=False)
    page: Page = await context.new_page()
    page.set_default_timeout(60000)

    print("Opening Shopby login page. Please complete login manually...")
    await page.goto(config.shopby.login_url, wait_until="domcontentloaded")

    # After initial login, the site may redirect to service.shopby login as well
    # User can navigate to orders page after login
    target_orders = config.shopby.orders_url
    print(f"After login, please navigate to: {target_orders}")

    # Poll until on orders page
    try:
        while True:
            await page.wait_for_timeout(1000)
            url = page.url
            if "service.shopby.co.kr" in url and ("/order/" in url or url.startswith(target_orders)):
                print("Detected Shopby service domain and orders area.")
                break
    except KeyboardInterrupt:
        pass

    # Save storage state
    state_path = config.data_dir / "shopby_state.json"
    await context.storage_state(path=str(state_path))
    print(f"Saved session to: {state_path}")

    # Keep window open briefly for user confirmation
    await page.wait_for_timeout(2000)
    await context.close()
    await browser.close()
    await p.stop()


if __name__ == "__main__":
    asyncio.run(main())







