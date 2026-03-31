import asyncio
from playwright.async_api import async_playwright

async def run():
    apis = []
    def handle_response(response):
        if response.request.resource_type in ["fetch", "xhr"]:
            apis.append(response.url)
            
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        page = await browser.new_page()
        page.on("response", handle_response)
        await page.goto("https://products.opustone.com/products", wait_until="networkidle")
        await asyncio.sleep(5)
        
        for url in set(apis):
            print("FOUND RAW API:", url)
        
        await browser.close()

asyncio.run(run())
