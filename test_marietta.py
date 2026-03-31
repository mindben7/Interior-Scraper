import asyncio
from src.scraper import InteriorScraper

async def main():
    scraper = InteriorScraper()
    await scraper.init_browser()
    images = await scraper.extract_images_from_page("https://www.mariettaleung.com")
    print(f"Found {len(images)} images.")
    for img in images:
        print(f" - {img}")
    await scraper.close_browser()

if __name__ == "__main__":
    asyncio.run(main())
