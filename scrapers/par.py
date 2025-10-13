from playwright.async_api import async_playwright
import asyncio

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto("https://example.com")

        # Type into the field character by character
        await page.locator("#area").press_sequentially("Hello World!", delay=150)

        await asyncio.sleep(3)
        await browser.close()

asyncio.run(run())
