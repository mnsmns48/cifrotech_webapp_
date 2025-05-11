from playwright.async_api import Playwright, Browser, async_playwright
from playwright_stealth import stealth_async

from utils import responses


async def run_browser(playwright: Playwright) -> Browser:
    browser = await playwright.chromium.launch(headless=True)
    return browser


async def open_link(url: str) -> str | dict:
    async with async_playwright() as playwright:
        browser = await run_browser(playwright)
        context = await browser.new_context()
        await context.set_extra_http_headers(
            {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/100.0.4896.75 Safari/537.36",
             "Accept-Language": "en-US,en;q=0.9",
             "Referer": "https://google.com"})
        page = await context.new_page()
        await stealth_async(page)
        await page.goto(url=url, wait_until='domcontentloaded')
        html = await page.locator("xpath=//body").inner_html()
        if html:
            return responses(html, True)
        return responses(f'Error HTML-code in {url}', False)
