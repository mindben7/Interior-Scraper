import asyncio
import yaml
import os
import sys

# Auto-installer for instaloader
try:
    import instaloader
except ImportError:
    print("[*] Installing instaloader...")
    os.system("venv/bin/pip install instaloader")
    import instaloader

from src.downloader import ImageDownloader

async def main():
    print("[*] Loading IG Targets Config...")
    config_path = 'config/lighting_instagram.yaml'
    if not os.path.exists(config_path):
        print(f"[-] Missing {config_path}")
        return
        
    with open(config_path, 'r') as f:
        ig_cfg = yaml.safe_load(f)
        
    # Get the Florida list specifically as requested
    handles = [h['handle'] for h in ig_cfg.get('instagram_targets', {}).get('florida_small_custom', [])]
    limit = ig_cfg.get('settings', {}).get('target_images_per_profile', 50)
    out_dir = ig_cfg.get('settings', {}).get('output_dir', 'data/IG_Lighting')
    
    print(f"[*] Initializing Unified Vision Downloader (Lighting Mode)...")
    downloader = ImageDownloader(base_dir=out_dir, use_filter=True, modes=["lighting"])
    
    L = instaloader.Instaloader(quiet=True)
    
    for handle in handles:
        print(f"\n==========================================")
        print(f"[*] Scraping Instagram Handle: @{handle}")
        print(f"==========================================")
        try:
            profile = instaloader.Profile.from_username(L.context, handle)
            count = 0
            images_to_eval = []
            
            for post in profile.get_posts():
                if count >= limit:
                    break
                    
                if post.typename == 'GraphSidecar':
                    for node in post.get_sidecar_nodes():
                        if not node.is_video and count < limit:
                            images_to_eval.append({
                                'url': node.display_url,
                                'width': 1080,
                                'height': 1080,
                                'alt': post.caption or f"IG Post by {handle}",
                                'page_url': f"https://instagram.com/p/{post.shortcode}"
                            })
                            count += 1
                elif not post.is_video:
                    images_to_eval.append({
                        'url': post.url,
                        'width': 1080,
                        'height': 1080,
                        'alt': post.caption or f"IG Post by {handle}",
                        'page_url': f"https://instagram.com/p/{post.shortcode}"
                    })
                    count += 1
                    
            if images_to_eval:
                print(f"[*] Found {len(images_to_eval)} raw assets for @{handle}. Handing to Vision Agent...")
                saved = await downloader.download_batch(images_to_eval, handle)
                print(f"[+] Saved {saved} AI-Accepted assets for @{handle}.")
            else:
                print(f"[-] No usable images found for @{handle}.")
                
        except Exception as e:
            if "LoginRequiredException" in str(e) or "Redirected to login" in str(e):
                print(f"[-] Instagram Login Wall hit on @{handle}. Moving to next profile...")
            elif "ProfileNotExistsException" in str(e):
                print(f"[-] Profile @{handle} does not exist or is private.")
            else:
                print(f"[-] Error on @{handle}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
