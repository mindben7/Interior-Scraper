import asyncio
import aiohttp
import re

async def main():
    url = "https://www.architecturaldigest.com/sitemap.xml?year=2024&month=2&week=3"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url) as res:
            text = await res.text()
            print(f"Status: {res.status}, Length: {len(text)}")
            locs = re.findall(r'<loc>(.*?)</loc>', text, re.IGNORECASE)
            print(f"Found {len(locs)} locs.")
            if locs:
                print(f"First 5: {locs[:5]}")

asyncio.run(main())
