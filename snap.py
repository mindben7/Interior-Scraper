import asyncio
from playwright.async_api import async_playwright
async def run():
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://products.opustone.com/products", wait_until="networkidle")
        await asyncio.sleep(5)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(3)
        await page.screenshot(path="opustone_target.jpg", full_page=True)
        print("Snapped opustone_target.jpg")
        await browser.close()
asyncio.run(run())
