import random
import asyncio
from contextlib import asynccontextmanager

from playwright.async_api import async_playwright, Browser, BrowserContext

import config


_browser: Browser | None = None
_pw = None


async def get_browser() -> Browser:
    global _browser, _pw
    if _browser is None or not _browser.is_connected():
        _pw = await async_playwright().start()
        _browser = await _pw.chromium.launch(headless=True)
    return _browser


@asynccontextmanager
async def new_context():
    browser = await get_browser()
    ua = random.choice(config.USER_AGENTS)
    context = await browser.new_context(
        user_agent=ua,
        viewport={"width": 1920, "height": 1080},
        locale="en-US",
    )
    try:
        yield context
    finally:
        await context.close()


async def random_delay(min_s: float = 3.0, max_s: float = 8.0) -> None:
    delay = random.uniform(min_s, max_s)
    await asyncio.sleep(delay)


async def close_browser() -> None:
    global _browser, _pw
    if _browser and _browser.is_connected():
        await _browser.close()
        _browser = None
    if _pw:
        await _pw.stop()
        _pw = None
