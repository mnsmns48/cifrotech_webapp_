from playwright.async_api import Playwright, Browser, async_playwright, Page
from playwright_stealth import stealth_async

from app_utils import responses
from config import settings, BROWSER_HEADERS



async def create_browser(playwright: Playwright) -> Browser:
    browser = await playwright.chromium.launch(headless=settings.parsing.browser_headless)
    return browser


async def run_browser() -> tuple[Playwright, Browser, Page]:
    playwright = await async_playwright().start()
    browser = await create_browser(playwright)
    context = await browser.new_context()
    await context.set_extra_http_headers(BROWSER_HEADERS)
    page = await context.new_page()
    await stealth_async(page)
    return playwright, browser, page


async def open_page(page: Page, url: str) -> dict:
    await page.goto(url, wait_until='domcontentloaded')
    html = await page.locator("xpath=//body").inner_html()
    if html:
        return responses(html, True, '')
    return responses(f'Error HTML-code in {url}', False)