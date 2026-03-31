import asyncio
from playwright.async_api import async_playwright

async def run():
    try:
        async with async_playwright() as p:
            browser = await p.firefox.launch(headless=True)
            page = await browser.new_page()
            await page.goto('https://products.opustone.com/products')
            await asyncio.sleep(4)
            
            # Check for load more buttons
            buttons = await page.evaluate("""
                Array.from(document.querySelectorAll('button, a, div, span')).filter(b => {
                    let t = b.innerText || b.textContent || '';
                    return t.toLowerCase().includes('more') || t.toLowerCase().includes('next') || t.toLowerCase().includes('load');
                }).map(b => ({tag: b.tagName, text: b.innerText, class: b.className}))
            """)
            print("Buttons found via JS:", buttons)

            await browser.close()
    except Exception as e:
        print("Script failed:", e)

asyncio.run(run())
