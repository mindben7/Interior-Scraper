import os
import io
import json
import asyncio
from PIL import Image

import sys
sys.stdout.reconfigure(line_buffering=True)

# Adjust path to safely import core modules inside the workspace
sys.path.append("/Users/ben/.gemini/antigravity/playground/ghost-spirit")
from src.filter import AgentFilter

TARGET_FOLDERS = [
    "/Users/ben/.gemini/antigravity/playground/ghost-spirit/data/images_wide",
    "/Users/ben/.gemini/antigravity/playground/ghost-spirit/data/images_detail",
    "/Users/ben/.gemini/antigravity/playground/ghost-spirit/data/images_lighting",
    "/Users/ben/.gemini/antigravity/playground/ghost-spirit/data/images_millwork",
    "/Volumes/BT4TB/_CLIENTS/Ruby/All Ruby Projects/Interior Designer Inspiration"
]

def load_global_metadata():
    db = {}
    meta_path = "/Users/ben/.gemini/antigravity/playground/ghost-spirit/data/metadata_global.jsonl"
    if os.path.exists(meta_path):
        with open(meta_path, 'r') as f:
            for line in f:
                try:
                    d = json.loads(line)
                    db[d['filename']] = d
                except: pass
    return db

async def process_legacy_assets():
    print("[*] INITIALIZING RETROACTIVE EXIF BURNER")
    img_filter = AgentFilter(modes=["wide", "detail", "lighting", "millwork"])
    meta_db = load_global_metadata()
    
    total_processed = 0

    for folder in TARGET_FOLDERS:
        print(f"\n=====================================")
        print(f"[*] Sweeping Directory: {folder}")
        print(f"=====================================")
        
        if not os.path.exists(folder):
            print(f"[-] Directory not found: {folder}. Skipping.")
            continue
            
        for root, _, files in os.walk(folder):
            for file in files:
                if not file.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                    continue
                    
                filepath = os.path.join(root, file)
                
                # Check if EXIF 270 already exists
                try:
                    with Image.open(filepath) as img:
                        exif = img.getexif()
                        if exif and 270 in exif and "Tags:" in str(exif[270]):
                            continue  # Already processed natively
                except Exception:
                    pass
                    
                print(f"    [>] AI Analyzing {file[:20]}...")
                try:
                    with open(filepath, 'rb') as f:
                        img_bytes = f.read()
                        
                    # Request pure Gemini Analysis to retroactively generate tags
                    result = await asyncio.to_thread(img_filter.evaluate_image, img_bytes)
                    category = result.get('category', 'UNCATEGORIZED')
                    tags = result.get('tags', '')
                    
                    # Merge with existing JSON metadata if it originated from the scraper
                    entry = meta_db.get(file, {})
                    pub = entry.get('publication', 'Designer Archive')
                    src = entry.get('source_url', 'Local Disk Vault')
                    cat = entry.get('assigned_category', category).upper()
                    
                    exif_desc = f"Publisher: {pub} | Source: {src} | Category: {cat} | Tags: {tags}"
                    
                    # Inject EXIF physically into bytes
                    with Image.open(io.BytesIO(img_bytes)) as img:
                        exif = img.getexif()
                        exif[270] = exif_desc
                        
                        if img.format == 'PNG':
                            from PIL.PngImagePlugin import PngInfo
                            metadata = PngInfo()
                            metadata.add_text("Description", exif_desc)
                            img.save(filepath, "PNG", pnginfo=metadata)
                        elif img.format in ['JPEG', 'WEBP', 'JPEG2000']:
                            if img.mode in ("RGBA", "P") and img.format == "JPEG":
                                img = img.convert("RGB")
                            img.save(filepath, img.format, exif=exif)
                        else:
                            # Fallback force JPEG encapsulation
                            if img.mode in ("RGBA", "P"):
                                img = img.convert("RGB")
                            img.save(filepath, "JPEG", exif=exif)
                            
                    total_processed += 1
                    print(f"    [+] EXIF Forged: {tags[:60]}...")
                except Exception as e:
                    print(f"    [-] Failed to process {file}: {e}")
                    
                # Strict sleep timer to guarantee we don't accidentally slam the API keys out of rotation bounds
                await asyncio.sleep(1.5)

    print(f"\n[*] ALL DIRECTORIES SWEPT. Total Legacy Assets Upgraded: {total_processed}")

if __name__ == "__main__":
    asyncio.run(process_legacy_assets())
