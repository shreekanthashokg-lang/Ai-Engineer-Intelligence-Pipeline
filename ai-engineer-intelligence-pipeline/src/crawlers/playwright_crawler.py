"""Playwright Async crawler — last resort in the access-method priority order
(official API > RSS > structured endpoint > plain HTTP > Playwright), used only for
publicly accessible pages that require JS rendering to produce their content (e.g.
a directory that client-side-renders its listing). Explicitly does NOT attempt to
solve CAPTCHAs, bypass login walls, or defeat Cloudflare/Datadome challenges —
those sources are documented as inaccessible per Phase V rather than bypassed
(see docs/anti_bot_strategy.md).
"""
from __future__ import annotations

import asyncio


async def render_page(url: str, wait_selector: str | None = None, timeout_ms: int = 20000) -> str:
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent="ai-engineer-intelligence-pipeline/0.1")
        try:
            await page.goto(url, timeout=timeout_ms, wait_until="networkidle")
            if wait_selector:
                await page.wait_for_selector(wait_selector, timeout=timeout_ms)
            html = await page.content()
        finally:
            await browser.close()
    return html


async def render_with_adaptive_delay(url: str, *, base_delay_s: float = 1.5) -> str:
    """Adds a small polite delay before rendering to avoid hammering JS-heavy
    public pages — part of the "adaptive rate limiting" behavior required for
    graceful degradation on sensitive sources."""
    await asyncio.sleep(base_delay_s)
    return await render_page(url)
