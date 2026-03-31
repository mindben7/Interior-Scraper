import asyncio
from playwright.async_api import async_playwright, Page
from urllib.parse import urljoin, urlparse

class InteriorScraper:
    def __init__(self, min_width=800, min_height=600):
        self.min_width = min_width
        self.min_height = min_height

    async def init_browser(self):
        self.playwright = await async_playwright().start()
        # Use chromium headless; ignore https errors for resilient scraping
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )

    async def close_browser(self):
        await self.browser.close()
        await self.playwright.stop()

    async def scroll_to_bottom(self, page: Page):
        """Scrolls the page to trigger lazy-loaded images."""
        try:
            await page.evaluate(
                """
                async () => {
                    await new Promise((resolve, reject) => {
                        let totalHeight = 0;
                        const distance = 500;
                        const timer = setInterval(() => {
                            const scrollHeight = document.body.scrollHeight;
                            window.scrollBy(0, distance);
                            totalHeight += distance;

                            if(totalHeight >= scrollHeight - window.innerHeight){
                                clearInterval(timer);
                                resolve();
                            }
                        }, 200);
                    });
                }
                """
            )
            # Wait a moment for final images to load after scrolling
            await page.wait_for_timeout(2000)
        except Exception as e:
            print(f"Error scrolling: {e}")

    async def extract_links_from_sitemap(self, url: str) -> set:
        """Attempts to find and parse /sitemap.xml for the domain instantaneously."""
        print(f"[*] Hunting for XML Sitemap on: {url}", flush=True)
        final_urls = set()
        base_domain = urlparse(url).netloc
        scheme = urlparse(url).scheme
        
        sitemap_urls = [
            f"{scheme}://{base_domain}/sitemap.xml",
            f"{scheme}://{base_domain}/sitemap_index.xml"
        ]
        
        import aiohttp
        import re
        
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}
        async with aiohttp.ClientSession(headers=headers) as session:
            for sitemap_url in sitemap_urls:
                try:
                    async with session.get(sitemap_url, timeout=10) as response:
                        if response.status == 200:
                            content = await response.text()
                            locs = re.findall(r'<loc>(.*?)</loc>', content, re.IGNORECASE)
                            
                            xml_hunts = []
                            for loc in locs:
                                if '.xml' in loc.lower():
                                    xml_hunts.append(loc)
                                else:
                                    parsed_loc = urlparse(loc)
                                    if parsed_loc.netloc == base_domain:
                                        banned_paths = ['/cart', '/checkout', '/account', '/contact', '/about', '/info', '/author', '/tag', '/search', '/policy', '/terms', '/privacy', 'login', '.jpg', '.png', '.webp']
                                        if len(parsed_loc.path) > 1 and parsed_loc.path != "/":
                                            if not any(bp in parsed_loc.path.lower() for bp in banned_paths):
                                                final_urls.add(loc)
                                                
                            if xml_hunts:
                                import random
                                random.shuffle(xml_hunts)
                                print(f"    [*] XML Router: Shuffling {len(xml_hunts)} nested paginations. Inspecting a random subset...", flush=True)
                                async def fetch_sub_sitemap(sub_url):
                                    try:
                                        async with session.get(sub_url, timeout=10) as sub_res:
                                            if sub_res.status == 200:
                                                sub_content = await sub_res.text()
                                                sub_locs = re.findall(r'<loc>(.*?)</loc>', sub_content, re.IGNORECASE)
                                                for sub_loc in sub_locs:
                                                    if '.xml' not in sub_loc.lower():
                                                        parsed_sub = urlparse(sub_loc)
                                                        banned_paths = ['/cart', '/checkout', '/account', '/contact', '/about', '/info', '/author', '/tag', '/search', '/policy', '/terms', '/privacy', 'login', '.jpg', '.png', '.webp']
                                                        if len(parsed_sub.path) > 1 and parsed_sub.path != "/":
                                                            if not any(bp in parsed_sub.path.lower() for bp in banned_paths):
                                                                final_urls.add(sub_loc)
                                    except Exception as e: pass

                                print(f"    [*] XML Throttler: Unrolling 10 sitemaps sequentially...", flush=True)
                                for su in xml_hunts[:10]:
                                    await fetch_sub_sitemap(su)
                                    await asyncio.sleep(0.5)
                            
                            if final_urls:
                                print(f"    [+] Successfully ripped {len(final_urls)} URIs from XML topography.", flush=True)
                                return final_urls
                            else:
                                print(f"    [!] XML Sub-hunts yielded 0 valid article URIs. Reverting.", flush=True)
                except Exception as e:
                    print(f"    [!] Root Sitemap Exception: {e}")
        return final_urls

    async def extract_links_from_homepage(self, url: str) -> set:
        """Finds links to articles/projects on a homepage."""
        print(f"[*] Discovering links on homepage: {url}")
        links = set()
        try:
            page = await self.context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self.scroll_to_bottom(page)
            
            # Extract all anchor tags with hrefs
            hrefs = await page.eval_on_selector_all(
                "a[href]", "elements => elements.map(el => el.getAttribute('href'))"
            )
            
            base_domain = urlparse(url).netloc
            for href in hrefs:
                if not href or href.startswith('javascript:'):
                    continue
                # Normalize URL
                full_url = urljoin(url, href)
                parsed_full = urlparse(full_url)
                
                # Basic heuristic: ensure it's on the same domain and looks like an article
                if parsed_full.netloc == base_domain:
                    # Filter out purely structural links (like # or just /)
                    if len(parsed_full.path) > 1 and parsed_full.path != "/":
                        # Aggressive Structural Firewall (Removed product/shop filters to allow high-end lighting assets)
                        banned_paths = ['/cart', '/checkout', '/account', '/contact', '/about', '/info', '/author', '/tag', '/search', '/policy', '/terms', '/privacy', 'login']
                        if not any(bp in parsed_full.path.lower() for bp in banned_paths):
                            links.add(full_url)
            
            await page.close()
        except Exception as e:
            print(f"[-] Failed to extract links from {url}: {e}")
        
        return links

    async def extract_images_from_page(self, url: str) -> list:
        """Navigates to an article page, scrolls, and extracts high-res images."""
        print(f"[*] Extracting images from: {url}")
        high_res_images = []
        try:
            page = await self.context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self.scroll_to_bottom(page)

            # Use JavaScript to evaluate natural dimensions, forcibly ripping data-src for Ecommerce stores
            images_data = await page.eval_on_selector_all(
                "img", 
                """elements => elements.map(img => {
                    let true_src = img.currentSrc || img.getAttribute('data-src') || img.getAttribute('data-lazy-src') || img.src;
                    let is_lazy = img.hasAttribute('data-src') || img.hasAttribute('data-lazy-src') || (true_src && true_src.includes('cdn.shopify'));
                    
                    try {
                        let srcset = img.getAttribute('data-srcset') || img.getAttribute('srcset') || "";
                        
                        let picture = img.closest('picture');
                        if (picture) {
                            let sourceEls = Array.from(picture.querySelectorAll('source'));
                            sourceEls.forEach(srcEl => {
                                let s = srcEl.getAttribute('data-srcset') || srcEl.getAttribute('srcset');
                                if (s) srcset += (srcset ? ", " : "") + s;
                            });
                        }

                        if (srcset) {
                            let sources = srcset.split(/,\\s+/).map(s => s.trim().split(/\\s+/));
                            sources.sort((a, b) => {
                                let aw = a[1] ? parseInt(a[1]) : 0;
                                let bw = b[1] ? parseInt(b[1]) : 0;
                                return bw - aw;
                            });
                            if (sources.length > 0 && sources[0][0]) {
                                true_src = sources[0][0];
                                is_lazy = true; 
                            }
                        }
                    } catch(e) {}
                    
                    if (true_src && typeof true_src === 'string') {
                        // Force Conde Nast / Fastly CDNs to serve uncompressed master widths
                        true_src = true_src.replace(/w_\\d+,c_limit/g, 'w_2560,c_limit');
                        true_src = true_src.replace(/[\\?&]w=\\d+/g, (match) => match.includes('?') ? '?w=2560' : '&w=2560');
                    }
                    
                    return {
                        src: true_src,
                        width: is_lazy ? 2560 : (img.naturalWidth || img.width || 0),
                        height: is_lazy ? 2560 : (img.naturalHeight || img.height || 0),
                        alt: img.alt || ''
                    };
                })"""
            )

            for img in images_data:
                src = img.get('src')
                # Ignore data URLs or empty sources
                if not src or src.startswith('data:'):
                    continue
                
                # Check resolution
                width = img.get('width', 0)
                height = img.get('height', 0)
                
                # Check for structural or generic lifestyle photography buzzwords to drop for free
                garbage_keywords = ['logo', 'icon', 'avatar', 'portrait', 'footer', 'nav', 'menu', 'cart', 'search', 'facebook', 'twitter', 'instagram', 'pinterest', 'banner', 'button', 'founder', 'team', 'svg']
                raw_txt = (str(src) + " " + str(img.get('alt', ''))).lower()
                is_garbage = any(kw in raw_txt for kw in garbage_keywords)
                
                if width >= self.min_width and height >= self.min_height and not is_garbage:
                    # Clean the URL (remove query params often used for sizing down, though this varies by CDN)
                    clean_url = urljoin(url, src)
                    high_res_images.append({
                        "url": clean_url,
                        "width": width,
                        "height": height,
                        "alt": img.get('alt', ''),
                        "page_url": url
                    })

            await page.close()
        except Exception as e:
            print(f"[-] Failed to extract images from {url}: {e}")
            
        return high_res_images

    async def extract_outbound_links(self, url: str) -> set:
        """Finds links to other seemingly relevant interior/architecture domains."""
        print(f"[*] Discovering outbound links on: {url}")
        outbound = set()
        try:
            page = await self.context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            hrefs = await page.eval_on_selector_all(
                "a[href]", "elements => elements.map(el => el.getAttribute('href'))"
            )
            
            base_domain = urlparse(url).netloc
            for href in hrefs:
                if not href or href.startswith('javascript:'):
                    continue
                full_url = urljoin(url, href)
                parsed = urlparse(full_url)
                
                # Check if it goes to a different domain
                if parsed.netloc and parsed.netloc != base_domain:
                    # Ignore common social/ad/infrastructure links
                    ignore = ['facebook', 'twitter', 'instagram', 'pinterest', 'google', 'apple', 'amazon', 'youtube', 'linkedin', 'tiktok', 'mail', 'tel']
                    if not any(ig in parsed.netloc.lower() for ig in ignore):
                        outbound.add(f"{parsed.scheme}://{parsed.netloc}/")
                        
            await page.close()
        except Exception as e:
            print(f"[-] Failed to extract outbound links from {url}: {e}")
            
        return outbound

    async def extract_ig_profile(self, handle: str, limit: int = 50) -> list:
        print(f"[*] Syncing Native Chrome Profile for IG Handle: {handle}")
        try:
            import browser_cookie3
            cj = browser_cookie3.chrome(domain_name='.instagram.com')
            cookies = [{'name': str(c.name), 'value': str(c.value), 'domain': str(c.domain), 'path': str(c.path), 'secure': bool(c.secure)} for c in cj]
            await self.context.add_cookies(cookies)
        except Exception:
            pass
            
        url = f"https://www.instagram.com/{handle}/"
        images = []
        try:
            page = await self.context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)
            
            last_height = 0
            while len(images) < limit:
                img_elements = await page.eval_on_selector_all(
                    "img", "elements => elements.map(e => ({src: e.src, w: e.naturalWidth, h: e.naturalHeight, alt: e.alt}))"
                )
                for img in img_elements:
                    src = img.get('src')
                    if src and 'scontent' in src and img.get('w', 0) > 150:
                        if not any(i['url'] == src for i in images):
                            images.append({
                                'url': src,
                                'width': img.get('w', 1080),
                                'height': img.get('h', 1080),
                                'alt': img.get('alt', ''),
                                'page_url': url
                            })
                            if len(images) >= limit: break
                
                if len(images) >= limit: break
                
                current_height = await page.evaluate("document.body.scrollHeight")
                if current_height == last_height:
                    await page.wait_for_timeout(2000)
                    new_height = await page.evaluate("document.body.scrollHeight")
                    if new_height == last_height: break
                
                last_height = current_height
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1500)
                
            await page.close()
        except Exception as e:
            print(f"[-] Playwright IG extraction error: {e}")
        return images[:limit]

    async def extract_pinterest_board(self, url: str, limit: int = 500) -> list:
        print(f"[*] Breaching Pinterest Board: {url} | Target Limit: {limit} assets")
        high_res_images = []
        try:
            page = await self.context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(3500)

            last_height = 0
            while len(high_res_images) < limit:
                img_elements = await page.eval_on_selector_all(
                    "img", "elements => elements.map(e => ({src: e.src, alt: e.alt}))"
                )
                
                for img in img_elements:
                    src = img.get('src', '')
                    if 'i.pinimg.com' in src:
                        # Break physical CDN downsampling limits
                        for low_res in ['/236x/', '/474x/', '/736x/']:
                            if low_res in src:
                                src = src.replace(low_res, '/originals/')
                                break
                        
                        if not any(i['url'] == src for i in high_res_images):
                            high_res_images.append({
                                'url': src,
                                'width': 1500,  # Assumed default standard for originals
                                'height': 1500,
                                'alt': img.get('alt', ''),
                                'page_url': url
                            })
                            if len(high_res_images) >= limit: break
                            
                if len(high_res_images) >= limit: break
                
                current_height = await page.evaluate("document.body.scrollHeight")
                if current_height == last_height:
                    await page.wait_for_timeout(2500)
                    new_height = await page.evaluate("document.body.scrollHeight")
                    if new_height == last_height: 
                        print("[*] Exhausted infinite scroll natively on Pinterest Board.")
                        break
                
                last_height = current_height
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1000)
                if len(high_res_images) > 0 and len(high_res_images) % 50 == 0:
                    print(f"[*] Spooling Pinterest Extraction... {len(high_res_images)} assets acquired from memory.")

            await page.close()
        except Exception as e:
            print(f"[-] Playwright Pinterest extraction error: {e}")

        return high_res_images[:limit]

# Simple test block
if __name__ == "__main__":
    async def main():
        scraper = InteriorScraper()
        await scraper.init_browser()
        links = await scraper.extract_links_from_homepage("https://design-milk.com/category/interior-design/")
        print(f"Found {len(links)} article links.")
        if links:
            test_link = list(links)[0]
            images = await scraper.extract_images_from_page(test_link)
            print(f"Found {len(images)} high-res images in {test_link}:")
            for img in images:
                print(f" - {img['url']} ({img['width']}x{img['height']})")
        await scraper.close_browser()

    asyncio.run(main())
