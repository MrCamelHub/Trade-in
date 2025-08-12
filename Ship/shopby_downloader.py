from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

from playwright.async_api import BrowserContext

from .config import AppConfig, ensure_data_dirs
from .browser_utils import start_browser


class ShopbyDownloader:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        ensure_data_dirs(self.config.data_dir)

    async def _new_context(self, download_dir: Path) -> BrowserContext:
        browser, context, p = await start_browser(headless=True)
        # Load saved auth state if exists to skip login
        state_path = self.config.data_dir / "shopby_state.json"
        storage_state = str(state_path) if state_path.exists() else None
        context = await browser.new_context(
            accept_downloads=True,
            record_har_path=str(self.config.data_dir / "logs" / f"shopby_{datetime.now().strftime('%Y%m%d_%H%M%S')}.har"),
            storage_state=storage_state,
        )
        # Force downloads into our path by intercepting Download object later
        self._playwright = p
        self._browser = browser
        return context

    async def download_orders_excel(self) -> Path:
        downloads_dir = self.config.data_dir / "downloads"
        outputs_dir = self.config.data_dir / "outputs"
        ensure_data_dirs(self.config.data_dir)

        context = await self._new_context(downloads_dir)
        page = await context.new_page()
        page.set_default_timeout(30000)

        # Try going directly with stored session; if not authenticated, fallback to login flow
        await page.goto(self.config.shopby.orders_url, wait_until='domcontentloaded')
        is_on_orders = "order/list" in page.url
        if not is_on_orders:
            await page.goto(self.config.shopby.login_url, wait_until="domcontentloaded")
        # Try multiple selector combinations for login
        selector_sets = [
            ('#username', '#password', 'button[type="submit"]'),
            ('input[name="username"]', 'input[name="password"]', 'button[type="submit"]'),
            ('#username', '#password', 'button:has-text("로그인")'),
            ('input[name="id"]', 'input[name="password"]', 'button[type="submit"]'),
            ('input[name="userId"]', 'input[name="password"]', 'button[type="submit"]'),
            ('#id', '#password', 'button[type="submit"]'),
            ('input#loginId', 'input#password', 'button[type="submit"]'),
            ('input[name="loginId"]', 'input[name="password"]', 'button[type="submit"]'),
            ('input[type="email"]', 'input[type="password"]', 'button[type="submit"]'),
        ]
        logged = False
        for id_sel, pw_sel, submit_sel in selector_sets:
            try:
                await page.wait_for_timeout(500)
                # Try in main page
                try:
                    await page.wait_for_selector(id_sel, timeout=3000)
                    target = page
                except Exception:
                    # Try in iframes
                    target = None
                    for fr in page.frames:
                        if fr is page.main_frame:
                            continue
                        try:
                            await fr.wait_for_selector(id_sel, timeout=1000)
                            target = fr
                            break
                        except Exception:
                            continue
                    if target is None:
                        raise
                await target.fill(id_sel, self.config.shopby.username)
                await target.wait_for_selector(pw_sel, timeout=5000)
                await target.fill(pw_sel, self.config.shopby.password)
                # Submit via click then Enter as fallback
                try:
                    await target.click(submit_sel, timeout=5000)
                except Exception:
                    # Focus password and press Enter
                    await target.focus(pw_sel)
                    await target.keyboard.press('Enter')
                try:
                    await page.wait_for_url("**service.shopby.co.kr**", timeout=15000)
                except Exception:
                    await page.wait_for_load_state('networkidle', timeout=15000)
                logged = True
                break
            except Exception:
                continue
        if not logged:
            # Final fallback: press Enter
            await page.keyboard.press('Enter')
            try:
                await page.wait_for_url("**service.shopby.co.kr**", timeout=15000)
            except Exception:
                await page.wait_for_load_state('networkidle', timeout=15000)

        # Navigate to orders list
        await page.wait_for_load_state('networkidle')
        # If we are on service login page, attempt second-phase login
        if "service.shopby.co.kr/login" in page.url:
            second_phase_sets = [
                ('#username', '#password', 'button[type="submit"]'),
                ('input[name="username"]', 'input[name="password"]', 'button[type="submit"]'),
                ('#username', '#password', 'button:has-text("로그인")'),
            ]
            for id_sel, pw_sel, submit_sel in second_phase_sets:
                try:
                    await page.wait_for_selector(id_sel, timeout=3000)
                    await page.fill(id_sel, self.config.shopby.username)
                    await page.wait_for_selector(pw_sel, timeout=3000)
                    await page.fill(pw_sel, self.config.shopby.password)
                    try:
                        await page.click(submit_sel, timeout=3000)
                    except Exception:
                        await page.focus(pw_sel)
                        await page.keyboard.press('Enter')
                    break
                except Exception:
                    continue
            await page.wait_for_load_state('networkidle')

        try:
            if "service.shopby.co.kr" not in page.url:
                await page.goto(self.config.shopby.orders_url, wait_until='networkidle')
        except Exception:
            await page.goto(self.config.shopby.orders_url, wait_until='networkidle')
        # Force reload once to ensure toolbar buttons are hydrated
        try:
            await page.wait_for_timeout(800)
            await page.goto(self.config.shopby.orders_url, wait_until='networkidle')
            await page.reload(wait_until='networkidle')
        except Exception:
            pass
        # Wait for export button to be attached/visible; try multiple candidates
        export_candidates = [
            'button.fixed_excel_download',
            # Explicit XPath from config
            f'xpath={self.config.shopby.export_button_xpath}',
            # Dropdown first: 클릭 → 엑셀 다운로드 항목 클릭
            'button:has-text("다운로드")',
            'text=다운로드',
            # Direct excel labels
            'text=엑셀 다운로드',
            'button:has-text("엑셀")',
            'button:has-text("Excel")',
            'text=내보내기',
        ]
        clicked = False
        for sel in export_candidates:
            try:
                await page.wait_for_selector(sel, timeout=5000)
                # If this is the dropdown, click it then click the Excel item
                if '다운로드' in sel and sel != 'button.fixed_excel_download':
                    await page.click(sel)
                    # Now click the excel item and wait for download at context level
                    async with context.expect_event('download') as download_info:
                        # Try common menu item texts
                        for item in ['엑셀 다운로드', '엑셀', 'Excel']:
                            try:
                                await page.click(f'text={item}', timeout=2000)
                                break
                            except Exception:
                                continue
                    download = await download_info.value
                else:
                    # Prefer evaluating click to bypass coverings
                    element_clicked = await page.evaluate(
                        "(sel) => { const el = document.querySelector(sel); if (el) { el.click(); return true;} return false; }",
                        sel
                    )
                    if not element_clicked:
                        await page.click(sel)
                    async with context.expect_event('download') as download_info:
                        # some UIs trigger download slightly after click
                        await page.wait_for_timeout(500)
                    download = await download_info.value
                clicked = True
                break
            except Exception:
                continue
        if not clicked:
            # Heuristic: click any visible button containing text 엑셀/다운로드
            try:
                handle = await page.evaluate_handle(
                    "() => {\n"
                    "  const els = Array.from(document.querySelectorAll('button, [role=button], a'));\n"
                    "  return els.map(e => ({text: (e.innerText||'').trim(), clickable: e.offsetParent !== null}));\n"
                    "}"
                )
                items = await handle.json_value()
                # Try click "다운로드" first to open menu
                for target_text in ["다운로드", "엑셀", "Excel"]:
                    try:
                        async with context.expect_event('download') as download_info:
                            await page.evaluate(
                                "(t) => {\n"
                                "  const els = Array.from(document.querySelectorAll('button, [role=button], a'));\n"
                                "  for (const e of els) {\n"
                                "    const tx = (e.innerText||'').trim();\n"
                                "    if (tx.includes(t) && e.offsetParent !== null) { e.click(); return true; }\n"
                                "  }\n"
                                "  return false;\n"
                                "}", target_text
                            )
                        download = await download_info.value
                        clicked = True
                        break
                    except Exception:
                        # Possibly opened a menu, now try clicking 엑셀 항목 without expecting download wrapper
                        try:
                            # Try inside any iframe as well
                            clicked_inside = False
                            for fr in page.frames:
                                try:
                                    await fr.click('text=엑셀', timeout=1000)
                                    clicked_inside = True
                                    break
                                except Exception:
                                    continue
                            if not clicked_inside:
                                await page.click('text=엑셀', timeout=2000)
                            # After clicking menu item, expect download
                            async with context.expect_event('download') as download_info2:
                                # sometimes clicking again triggers the actual download
                                await page.wait_for_timeout(500)
                            download = await download_info2.value
                            clicked = True
                            break
                        except Exception:
                            continue
            except Exception:
                pass
        if not clicked:
            # Save diagnostics
            logs_dir = self.config.data_dir / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            await page.screenshot(path=str(logs_dir / "shopby_export_not_found.png"), full_page=True)
            html = await page.content()
            (logs_dir / "shopby_export_not_found.html").write_text(html, encoding='utf-8')
            raise RuntimeError("Export button not found - screenshot and HTML dumped to logs")


        # Build deterministic output filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        target_path = downloads_dir / f"shopby_orders_{timestamp}.xlsx"
        await download.save_as(str(target_path))

        # Save storage state for future runs (post-login)
        try:
            await context.storage_state(path=str(self.config.data_dir / "shopby_state.json"))
        except Exception:
            pass

        await context.close()
        await self._browser.close()
        await self._playwright.stop()

        return target_path


async def download_latest_excel(config: AppConfig) -> Path:
    downloader = ShopbyDownloader(config)
    return await downloader.download_orders_excel()


