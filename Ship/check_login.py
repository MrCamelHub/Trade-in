from __future__ import annotations

import asyncio
from pathlib import Path

from .config import load_app_config, ensure_data_dirs
from .browser_utils import start_browser


async def check_login_once() -> str:
    config = load_app_config()
    ensure_data_dirs(config.data_dir)
    browser, context, p = await start_browser(headless=False)
    # accept downloads not needed here
    page = await context.new_page()
    page.set_default_timeout(30000)
    await page.goto(config.shopby.login_url, wait_until="domcontentloaded")
    # Try login selectors (exact ones provided by user first)
    selector_sets = [
        ('#username', '#password', 'button[type="submit"]'),
        ('input[name="username"]', 'input[name="password"]', 'button[type="submit"]'),
        ('#username', '#password', 'button:has-text("로그인")'),
    ]
    for id_sel, pw_sel, submit_sel in selector_sets:
        try:
            await page.wait_for_selector(id_sel, timeout=5000)
            await page.fill(id_sel, config.shopby.username)
            await page.wait_for_selector(pw_sel, timeout=5000)
            await page.fill(pw_sel, config.shopby.password)
            try:
                await page.click(submit_sel, timeout=5000)
            except Exception:
                await page.focus(pw_sel)
                await page.keyboard.press('Enter')
            try:
                await page.wait_for_url("**service.shopby.co.kr**", timeout=20000)
            except Exception:
                await page.wait_for_load_state('networkidle', timeout=20000)
            break
        except Exception:
            continue

    # Go to orders page to ensure session is valid
    try:
        await page.goto(config.shopby.orders_url, wait_until='domcontentloaded')
    except Exception:
        pass

    logs_dir = config.data_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    shot = logs_dir / "shopby_login_check.png"
    await page.screenshot(path=str(shot), full_page=True)
    current_url = page.url
    await context.close()
    await browser.close()
    await p.stop()
    return current_url


if __name__ == "__main__":
    url = asyncio.run(check_login_once())
    print(f"Current URL after login: {url}")


