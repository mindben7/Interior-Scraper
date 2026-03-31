import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://www.mariettaleung.com")
        await page.wait_for_timeout(2000)
        
        images_data = await page.eval_on_selector_all(
            "img", 
            """elements => elements.map(img => {
                let true_src = img.currentSrc || img.getAttribute('data-src') || img.getAttribute('data-lazy-src') || img.src;
                let is_lazy = img.hasAttribute('data-src') || img.hasAttribute('data-lazy-src') || (true_src && true_src.includes('cdn.shopify'));
                
                let s_log = "no srcset";
                try {
                    let srcset = img.getAttribute('data-srcset') || img.getAttribute('srcset') || "";
                    if (srcset) {
                        let sources = srcset.split(',').map(s => s.trim().split(' '));
                        sources.sort((a, b) => {
                            let aw = a[1] ? parseInt(a[1]) : 0;
                            let bw = b[1] ? parseInt(b[1]) : 0;
                            return bw - aw;
                        });
                        s_log = sources.map(s => s[0] + "(" + s[1] + ")").join(" | ");
                        if (sources.length > 0 && sources[0][0]) {
                            true_src = sources[0][0];
                            is_lazy = true; // Flips logical dimensions to 1500x1500 to bypass DOM limits
                        }
                    }
                } catch(e) { s_log = e.toString(); }
                
                return {
                    src: true_src,
                    width: img.naturalWidth || img.width || (is_lazy ? 1500 : 0),
                    height: img.naturalHeight || img.height || (is_lazy ? 1500 : 0),
                    log: s_log
                };
            })"""
        )
        for i, img in enumerate(images_data[:5]):
            print(f"Img {i}: {img['width']}x{img['height']} | lazy: {img['width']==1500} | log: {img['log'][:100]}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
