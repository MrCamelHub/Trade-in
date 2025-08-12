from __future__ import annotations

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

from .config import AppConfig, ensure_data_dirs


class CornerLogisUploader:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        ensure_data_dirs(self.config.data_dir)

    async def upload_excel(self, excel_path: Path) -> None:
        p = await async_playwright().start()
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(self.config.cornerlogis.portal_url, wait_until='domcontentloaded')

        # Attempt basic login; selectors may need adjustment based on actual markup
        # Common names: username/password or id/pw
        # We try a few common patterns to minimize setup
        selectors = [
            ('input[name="id"]', 'input[name="pw"]', 'button[type="submit"]'),
            ('input[name="username"]', 'input[name="password"]', 'button[type="submit"]'),
        ]
        logged_in = False
        for id_sel, pw_sel, submit_sel in selectors:
            try:
                await page.fill(id_sel, self.config.cornerlogis.username)
                await page.fill(pw_sel, self.config.cornerlogis.password)
                await page.click(submit_sel)
                await page.wait_for_load_state('networkidle')
                logged_in = True
                break
            except Exception:
                continue

        if not logged_in:
            # Fallback: try pressing enter
            await page.keyboard.press('Enter')
            await page.wait_for_load_state('networkidle')

        # Upload flow
        await page.set_input_files(f'xpath={self.config.cornerlogis.file_input_xpath}', str(excel_path))
        await page.click(f'xpath={self.config.cornerlogis.upload_button_xpath}')

        # Optional: wait for success toast or result
        await page.wait_for_timeout(2000)

        await context.close()
        await browser.close()
        await p.stop()


async def upload_file(config: AppConfig, path: Path) -> None:
    uploader = CornerLogisUploader(config)
    await uploader.upload_excel(path)


