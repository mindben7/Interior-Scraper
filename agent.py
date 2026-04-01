import sys
sys.stdout.reconfigure(line_buffering=True)
import argparse
import asyncio
import os
import yaml
import random
import urllib.request
import sys
from urllib.parse import urlparse

from src.scraper import InteriorScraper
from src.downloader import ImageDownloader

async def run_agent(modes, target_url=None, chunk_index=0, chunk_total=1):
    modes_str = ", ".join(modes).upper()
    print(f"[*] Starting SYSTEM OVERRIDE: Unified Agent running targeting: [{modes_str}]")
    
    # Dynamic External Volume Targeting
    EXTERNAL_VOLUME = "/Volumes/BT4TB/_CLIENTS/Ruby/All Ruby Projects/Interior Designer Inspiration"
    if os.path.exists(EXTERNAL_VOLUME):
        base_target = EXTERNAL_VOLUME
        print(f"[*] EXTERNAL DRIVE DETECTED: Rerouting all assets to {base_target}")
    else:
        base_target = "data"
        print(f"[!] External Drive Missing. Falling back to local cache: ./data/")
        
    if "preset-contemporary" in modes_str.lower():
        base_target = os.path.join(base_target, "Studio Ramirez ROW01", "Furniture_Brands")
        print(f"[*] CONTEMPORARY PRESET: Routing to dedicated sub-folder -> {base_target}")
    elif "preset-architects" in modes_str.lower():
        base_target = os.path.join(base_target, "Studio Ramirez ROW01", "Master_Architects")
        print(f"[*] ARCHITECT PRESET: Routing to dedicated sub-folder -> {base_target}")
        
    os.makedirs(base_target, exist_ok=True)

    # Establish a universal global visited tracker for this master session
    visited_file = os.path.join(base_target, "visited_global_tracker.txt")
    swept_file = os.path.join(base_target, "swept_global_tracker.txt")

    seeds = []
    seen_urls = set()
    
    # 1. Explicit Single-Domain Override (From UI Dropdown)
    target_map = {
        "target-ad": "architecturaldigest.com",
        "target-woi": "worldofinteriors.com",
        "target-elle": "elledecor.com",
        "target-galerie": "galeriemagazine.com",
        "target-luxe": "luxesource.com",
        "target-vogue": "vogue.com.au/vogue-living",
        "target-1stdibs": "1stdibs.com/introspective-magazine",
        "target-interiordesign": "interiordesign.net",
        "target-wallpaper": "wallpaper.com",
        "target-yatzer": "yatzer.com",
        "target-yellowtrace": "yellowtrace.com.au",
        "target-covet": "covetedition.com",
        "target-robbreport": "robbreport.com",
        "target-hospitality": "hospitalitydesign.com",
        "target-coolhunter": "thecoolhunter.net",
        "target-surface": "surfacemag.com",
        "target-boca": "bocadolobo.com",
        "target-nuvo": "nuvomagazine.com",
        "target-haute": "hauteresidence.com"
    }
    
    selected_target = None
    for tm, domain in target_map.items():
        if tm in modes_str.lower():
            selected_target = domain
            break
            
    if selected_target:
        print(f"[*] EXPLICIT OVERRIDE DETECTED: Restricting crawler purely to -> {selected_target}")
        seeds.append({'url': f"https://www.{selected_target}" if "vogue" not in selected_target and "1stdibs" not in selected_target else f"https://www.{selected_target}"})
        # Try to pull the clean URL definition from the preset if possible
        if os.path.exists('config/top10_luxury_preset.yaml'):
            with open('config/top10_luxury_preset.yaml', 'r') as f:
                cfg = yaml.safe_load(f)
                for s in cfg.get('publications', []):
                    if isinstance(s, dict) and s.get('url') and selected_target in s.get('url'):
                        seeds = [s] # Hard overwrite with the clean yaml object
                        break
                        
    # 2. Top 10 Ultra-Luxury Preset Override
    elif "top10-luxury" in modes_str.lower():
        if os.path.exists('config/top10_luxury_preset.yaml'):
            with open('config/top10_luxury_preset.yaml', 'r') as f:
                cfg = yaml.safe_load(f)
                for s in cfg.get('publications', []):
                    if isinstance(s, dict) and s.get('url') and s.get('url') not in seen_urls:
                        seen_urls.add(s.get('url'))
                        seeds.append(s)
    
    # 2.5 Contemporary Design Preset
    elif "preset-contemporary" in modes_str.lower():
        if os.path.exists('config/contemporary_design.yaml'):
            with open('config/contemporary_design.yaml', 'r') as f:
                cfg = yaml.safe_load(f)
                for s in cfg.get('publications', []):
                    if isinstance(s, dict) and s.get('url') and s.get('url') not in seen_urls:
                        seen_urls.add(s.get('url'))
                        seeds.append(s)

    # 2.6 Master Architects Preset
    elif "preset-architects" in modes_str.lower():
        if os.path.exists('config/master_architects.yaml'):
            with open('config/master_architects.yaml', 'r') as f:
                cfg = yaml.safe_load(f)
                for s in cfg.get('publications', []):
                    if isinstance(s, dict) and s.get('url') and s.get('url') not in seen_urls:
                        seen_urls.add(s.get('url'))
                        seeds.append(s)
    else:
        # 3. Master Lighting Architecture Directory
        if "lighting" in modes:
            if os.path.exists('config/master_lighting.yaml'):
                with open('config/master_lighting.yaml', 'r') as f:
                    cfg = yaml.safe_load(f)
                    for s in cfg.get('publications', []):
                        if isinstance(s, dict) and s.get('url') and s.get('url') not in seen_urls:
                            seen_urls.add(s.get('url'))
                            seeds.append(s)
                            
        # 3. Instagram Lighting Targets
        if "lighting-ig" in modes:
            if os.path.exists('config/lighting_instagram.yaml'):
                with open('config/lighting_instagram.yaml', 'r') as f:
                    ig_cfg = yaml.safe_load(f)
                    targets = ig_cfg.get('instagram_targets', {})
                    if targets:
                        for cat, handles in targets.items():
                            if handles:
                                for h in handles:
                                    ig_url = f"https://www.instagram.com/{h['handle']}/"
                                    if ig_url not in seen_urls:
                                        seen_urls.add(ig_url)
                                        seeds.append({'url': ig_url})

        # 4. Master Interior Designers & Publishers Directory
        if any(m in modes for m in ["wide", "detail", "mood", "restaurant"]):
            if os.path.exists('config/master_interiors.yaml'):
                with open('config/master_interiors.yaml', 'r') as f:
                    cfg = yaml.safe_load(f)
                    for s in cfg.get('publications', []):
                        if isinstance(s, dict) and s.get('url') and s.get('url') not in seen_urls:
                            seen_urls.add(s.get('url'))
                            seeds.append(s)

    random.shuffle(seeds)

    # Settings fallback
    min_width = 800
    min_height = 600 if any(m in modes for m in ["wide", "detail", "vintage-editorial", "mood", "restaurant"]) else 800
    domain_limit = 1000 if any(m in modes for m in ["millwork", "lighting"]) else 500
    GLOBAL_TARGET = 30000
    total_downloaded = 0
    
    visited_domains = set()
    if os.path.exists(visited_file):
        with open(visited_file, "r") as vf:
            for line in vf: visited_domains.add(line.strip())
            
    swept_urls = set()
    if os.path.exists(swept_file):
        with open(swept_file, "r") as sf:
            for line in sf: swept_urls.add(line.strip())

    domain_queue = []
    is_explicit_run = selected_target or "top10-luxury" in modes_str.lower() or "preset-contemporary" in modes_str.lower() or "preset-architects" in modes_str.lower()
    for seed in seeds:
        url = seed.get('url')
        domain = urlparse(url).netloc
        cache_key = url if ("instagram.com" in domain or url.lower().endswith(".pdf")) else domain
        if is_explicit_run or cache_key not in visited_domains:
            domain_queue.append(url)

    if chunk_total > 1:
        domain_queue.sort() # Ensure deterministic slice across independent agent nodes
        import math
        chunk_size = math.ceil(len(domain_queue) / chunk_total)
        start = chunk_index * chunk_size
        end = start + chunk_size
        domain_queue = domain_queue[start:end]
        print(f"\n[*] SWARM SHARDING: Activated Agent {chunk_index+1}/{chunk_total}")
        print(f"    -> Agent assigned target block [{start}:{end}]: {len(domain_queue)} domains\n")

    # Initialize universal scraper and multi-mode downloader
    scraper = InteriorScraper(min_width=min_width, min_height=min_height)
    downloader = ImageDownloader(base_dir=base_target, use_filter=True, modes=modes)

    await scraper.init_browser()
    
    # EXPLICIT PINTEREST TARGETING OVERRIDE
    if target_url and 'pinterest.com' in target_url.lower():
        print(f"\n=====================================")
        print(f"[*] PINTEREST MASTER OVERRIDE: Launching Board Breaker Pipeline")
        print(f"[*] Target Board: {target_url}")
        print(f"=====================================")
        try:
            images = await scraper.extract_pinterest_board(target_url, limit=5000)
            if images:
                saved = await downloader.download_batch(images, "Pinterest_Archive")
                print(f"[*] Pinterest Harvesting Concluded. Captured {saved} authenticated master files.")
            else:
                print(f"[-] No valid imagery intercepted from target Pinterest board.")
        finally:
            await scraper.close_browser()
        return

    try:
        while domain_queue and total_downloaded < GLOBAL_TARGET:
            try:
                urllib.request.urlopen("http://127.0.0.1:5050/", timeout=1)
            except Exception:
                print("[!] DEAD MAN'S SWITCH TRIPPED: Orchestrator offline. Self-Terminating Pipeline.")
                sys.exit(1)
                
            current_url = domain_queue.pop(0)
            current_domain = urlparse(current_url).netloc
            cache_key = current_url if ("instagram.com" in current_domain or current_url.lower().endswith(".pdf")) else current_domain
            if not is_explicit_run and cache_key in visited_domains: continue
            
            print(f"\n=====================================")
            print(f"[*] MULTI-MODE Agent targeting: {cache_key}")
            print(f"[*] Queue Size: {len(domain_queue)} | Global Progress: {total_downloaded}/{GLOBAL_TARGET}")
            print(f"=====================================")

            # ----- INSTAGRAM OVERRIDE -----
            if "instagram.com" in current_domain:
                handle = current_url.strip('/').split('/')[-1]
                print(f"[*] Instagram target detected. Initiating Native Playwright DOM Extractor on @{handle}")
                pub_name = f"IG_{handle}"
                
                ig_limit = 50
                if os.path.exists('config/lighting_instagram.yaml'):
                    with open('config/lighting_instagram.yaml', 'r') as f:
                        ig_limit = yaml.safe_load(f).get('settings', {}).get('target_images_per_profile', 50)
                            
                images_to_eval = await scraper.extract_ig_profile(handle, limit=ig_limit)
                
                if images_to_eval:
                    new_images = []
                    for img in images_to_eval:
                        img_id = img['url'].split('?')[0] # Using base generic url for sweeping cache
                        if img_id not in swept_urls:
                            swept_urls.add(img_id)
                            new_images.append(img)
                            try:
                                with open(swept_file, "a") as sf: sf.write(f"{img_id}\n")
                            except: pass
                            
                    if new_images:
                        saved = await downloader.download_batch(new_images, pub_name)
                        total_downloaded += saved
                        print(f"[*] {pub_name} Progress: {saved}/{ig_limit} | Global: {total_downloaded}")
                    else:
                        print(f"[*] {pub_name}: All {len(images_to_eval)} retrieved images were already swept previously.")
                        
                visited_domains.add(cache_key)
                try:
                    with open(visited_file, "a") as vf: vf.write(f"{cache_key}\n")
                except: pass
                
                print("[*] Native Playwright processing complete. Cooldown enforced...")
                await asyncio.sleep(random.uniform(3.0, 7.0))
                continue
            # ----- END INSTAGRAM OVERRIDE -----

            if current_url.lower().endswith(".pdf"):
                article_links = []
                print(f"[*] Native PDF Target Detected: Bypassing HTML Link Extractor.")
            else:
                try:
                    article_links = await scraper.extract_links_from_sitemap(current_url)
                    if not article_links:
                        print(f"[*] XML Sitemap isolated/denied. Falling back to Visual DOM extraction...")
                        article_links = await scraper.extract_links_from_homepage(current_url)
                except Exception as e:
                    print(f"[-] Root crawler error on {current_url}: {e}")
                    article_links = []
                
            print(f"[*] Found {len(article_links)} article links on {current_domain}.")
            pub_name = current_domain.replace(".com", "").replace("www.", "").title()
            
            domain_downloaded = 0
            consecutive_empty_pages = 0

            # Dynamic Heuristic Scoring aggregating all active modes!
            def dynamic_score(u):
                s = 0
                u_lower = u.lower()
                
                # The "Universal Aesthetic" Booster (ALWAYS triggers across ALL presets)
                if any(w in u_lower for w in ['gallery', 'galleries', 'project', 'projects', 'portfolio', 'work', 'interior', 'space', 'architecture']):
                    s += 100
                
                if "millwork" in modes:
                    if any(w in u_lower for w in ['kitchen', 'wardrobe', 'cabinet', 'millwork', 'joinery', 'custom']): s += 20
                if "lighting" in modes:
                    if any(w in u_lower for w in ['lamp', 'pendant', 'sconce', 'chandelier', 'fixture', 'lighting', 'suspension']): s += 20
                if "detail" in modes:
                    if any(w in u_lower for w in ['/detail', '/object', '/styling', '/close', '/material', '/texture', '/furniture', '/finish', '/fabric']): s += 15
                if any(m.lower() in ["preset-contemporary", "preset-architects"] for m in modes):
                    # The "Elite Contemporary Master" Booster
                    if any(w in u_lower for w in ['villa', 'penthouse', 'contemporary', 'minimalist', 'italian', 'bespoke', 'modernism', 'dark', 'monochromatic', 'luxury', 'stone', 'marble']):
                        s += 80
                    
                # Universal Negative Heuristic (Dodge generic corporate pages and toxic design styles)
                if any(w in u_lower for w in ['/about', '/contact', '/privacy', '/terms', '/press', '/faq', '/cart', '/checkout', '/careers']):
                    s -= 200
                    
                return s + len(u.split('/'))

            # The Extreme Aesthetic Blocklist - Physically delete URLs pointing to wrong genres before they are scored
            toxic_keywords = ['farm', 'barn', 'cabin', 'tiny-home', 'diy', 'budget', 'affordable', 'rustic', 'cottage', 'coastal', 'beach', 'hamptons', 'midcentury', 'mid-century', 'traditional', 'victorian', 'country']
            clean_articles = [u for u in article_links if not any(tox in u.lower() for tox in toxic_keywords)]
            
            sorted_articles = sorted(list(clean_articles), key=dynamic_score, reverse=True)
            
            sorted_articles = [u for u in sorted_articles if u not in swept_urls]
            if current_url not in sorted_articles: sorted_articles.insert(0, current_url)

            if len(sorted_articles) == 1 and sorted_articles[0] == current_url:
                print(f"[*] INITIALIZING ROOT DOMAIN ONLY {pub_name}")
            elif not sorted_articles:
                print(f"[*] ERADICATING DOMAIN {pub_name} - No viable routing logic.")
                visited_domains.add(current_domain)
                try:
                    with open(visited_file, "a") as vf: vf.write(f"{current_domain}\n")
                except: pass
                continue

            print(f"[*] Ranked {len(sorted_articles)} optimal targets via fused multi-modal heuristics. Sweeping...")
            for i, article_url in enumerate(sorted_articles, 1):
                if total_downloaded >= GLOBAL_TARGET: break
                if domain_downloaded >= domain_limit:
                    print(f"[*] Reached target limit of {domain_limit} images for {pub_name}. Shuffling.")
                    break
                if consecutive_empty_pages >= 15:
                    print(f"[*] MICRO-PATIENCE PROTOCOL: Bailing out of {pub_name}! 15 consecutive empty prioritized targets.")
                    break
                
                print(f"    --> ({i}/{len(sorted_articles)}) Extracting Geometry: {article_url}")
                
                # Pre-emptively commit to ledger to prevent boot-loops on user-abort
                swept_urls.add(article_url)
                try:
                    with open(swept_file, "a") as sf: sf.write(f"{article_url}\n")
                except: pass
                
                try:
                    if article_url.lower().endswith(".pdf"):
                        print(f"[*] USModernist Archive PDF detected. Activating native PDF Extraction pipeline...")
                        import src.pdf_extractor as pdf_ex
                        images = await pdf_ex.extract_pdf_images(article_url)
                    else:
                        images = await scraper.extract_images_from_page(article_url)
                except Exception as e:
                    print(f"[-] Error extracting images: {e}")
                    images = []
                    
                try:
                    with open(os.path.join(base_target, "scanned_global_tracker.txt"), "a") as f:
                        f.write(f"{len(images)}\n")
                except: pass
                
                # Deep discovery
                try:
                    if scraper.page:
                        deep_links = await scraper.get_all_links(scraper.page, current_url)
                        for deep_u in deep_links:
                            if deep_u not in swept_urls and deep_u not in sorted_articles:
                                if any(k in deep_u.lower() for k in commerce_keys) and not any(junk in deep_u.lower() for junk in ['blog', 'news', 'about', 'contact']):
                                    sorted_articles.append(deep_u)
                except Exception: pass
                    
                if images:
                    filtered_images = []
                    denylist = ['logo', 'headshot', 'profile', 'icon', 'author', 'avatar', 'banner', 'newsletter']
                    for img in images:
                        alt_str = str(img.get('alt', '')).lower()
                        src_str = str(img.get('src', '')).lower()
                        if not any(d in alt_str or d in src_str for d in denylist):
                            filtered_images.append(img)
                    images = filtered_images
                
                if images:
                    print(f"    --> Found {len(images)} assets. JSON Evaluating dynamically across {len(modes)} categories...")
                    try:
                        saved_count = await downloader.download_batch(images, pub_name)
                    except Exception as e:
                        print(f"[-] Error downloading batch: {e}")
                        saved_count = 0
                        
                    if saved_count == 0: 
                        consecutive_empty_pages += 1
                    else: 
                        consecutive_empty_pages = 0
                    
                    total_downloaded += saved_count
                    domain_downloaded += saved_count
                    print(f"[*] {pub_name} Progress: {domain_downloaded}/{domain_limit} | Global: {total_downloaded}")
                else:
                    consecutive_empty_pages += 1
                
                # Deep discovery
                try:
                    if scraper.page:
                        deep_links = await scraper.get_all_links(scraper.page, current_url)
                        for deep_u in deep_links:
                            if deep_u not in swept_urls and deep_u not in sorted_articles:
                                if any(k in deep_u.lower() for k in commerce_keys) and not any(junk in deep_u.lower() for junk in ['blog', 'news', 'about', 'contact']):
                                    sorted_articles.append(deep_u)
                except Exception: pass
                
                await asyncio.sleep(1.5)
            visited_domains.add(current_domain)
            try:
                with open(visited_file, "a") as vf: vf.write(f"{current_domain}\n")
            except: pass
            print(f"[*] Finished {pub_name}. Global count: {total_downloaded}")
            
    finally:
        await scraper.close_browser()
        print(f"\n[*] MULTI-MODE Agent Halted. Total downloaded: {total_downloaded}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interiors Scraper Unified Agent")
    parser.add_argument('--modes', type=str, required=True, help='Comma separated modes (wide,detail,lighting,millwork)')
    parser.add_argument('--target-url', type=str, default=None, help='Explicit URL bypass')
    parser.add_argument('--chunk-index', type=int, default=0, help='Index for swarm sharding')
    parser.add_argument('--chunk-total', type=int, default=1, help='Total parallel chunks')
    args = parser.parse_args()
    
    active_modes = [m.strip().lower() for m in args.modes.split(',') if m.strip()]
    if not active_modes:
        print("[-] Must provide at least one mode flag.")
        sys.exit(1)
        
    asyncio.run(run_agent(active_modes, args.target_url, args.chunk_index, args.chunk_total))
