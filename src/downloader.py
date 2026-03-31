import os
import aiohttp
import asyncio
from urllib.parse import urlparse
import hashlib
import json
import io
from PIL import Image
from src.filter import AgentFilter

class ImageDownloader:
    def __init__(self, base_dir="data", use_filter=True, modes=None):
        self.base_dir = base_dir
        self.use_filter = use_filter
        self.modes = modes or ["wide"]
        
        self.img_filter = AgentFilter(modes=self.modes) if use_filter else None
        
        self.root_dir = "/Volumes/BT4TB/_CLIENTS/Ruby/All Ruby Projects/Interior Designer Inspiration"
        if not os.path.exists(self.root_dir):
            self.root_dir = "data"
            
        self.dir_mapping = {
            "wide": "Wides",
            "detail": "Macro_Textures",
            "lighting": "Lighting_Fixtures",
            "mood": "Moodboard_Abstracts",
            "restaurant": "High_End_Restaurants",
            "millwork": "Millwork_And_Joinery",
            "chair": "Designer_Chairs",
            "vintage-editorial": "Vintage_Editorial",
            "vintage-ad": "Vintage_Editorial/Ads"
        }
        
        for m in self.modes:
            folder = self.dir_mapping.get(m, m.capitalize())
            os.makedirs(os.path.join(self.base_dir, folder), exist_ok=True)
            if m == "vintage-editorial":
                os.makedirs(os.path.join(self.base_dir, "Vintage_Editorial/Ads"), exist_ok=True)
            
        self.hashes_file = os.path.join(self.root_dir, "known_hashes_global.txt")
        self.known_hashes = set()
        
        if os.path.exists(self.hashes_file):
            with open(self.hashes_file, "r") as f:
                for line in f:
                    self.known_hashes.add(line.strip())

    def _get_filename(self, url: str) -> str:
        clean_url = url.split('?')[0]
        url_hash = hashlib.md5(clean_url.encode('utf-8')).hexdigest()
        parsed_url = urlparse(clean_url)
        path = parsed_url.path
        ext = os.path.splitext(path)[1].lower()
        if not ext or ext not in ['.jpg', '.jpeg', '.png', '.webp', '.avif']:
            ext = '.jpg'
        return f"{url_hash}{ext}"

    def _is_pixel_duplicate(self, image_bytes: bytes) -> bool:
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                img = img.resize((9, 8), Image.Resampling.LANCZOS).convert('L')
                pixels = list(img.getdata())
                diff = []
                for row in range(8):
                    for col in range(8):
                        diff.append(pixels[row * 9 + col] > pixels[row * 9 + col + 1])
                
                decimal_value = 0
                hex_str = []
                for i, bit in enumerate(diff):
                    if bit: decimal_value += 2**(i % 8)
                    if (i % 8) == 7:
                        hex_str.append(hex(decimal_value)[2:].rjust(2, '0'))
                        decimal_value = 0
                img_hash = ''.join(hex_str)
        except:
            img_hash = hashlib.sha256(image_bytes).hexdigest()
            
        if img_hash in self.known_hashes:
            return True
            
        self.known_hashes.add(img_hash)
        try:
            with open(self.hashes_file, "a") as f:
                f.write(img_hash + "\n")
        except: pass
        return False

    async def download_image(self, session: aiohttp.ClientSession, img_dict: dict, publication_name: str) -> bool:
        url = img_dict['url']
        page_url = img_dict.get('page_url', url)
        filename = self._get_filename(url)

        try:
            if url.startswith('file://'):
                local_path = url[7:]
                with open(local_path, 'rb') as f:
                    data = f.read()
            else:
                async with session.get(url, timeout=20) as response:
                    if response.status != 200:
                        print(f"    [-] Failed to download {url} - Status: {response.status}", flush=True)
                        return False
                    data = await response.read()
                    
            # 1. File Size Quality Gate (Reject < 40KB entirely to allow modern WebP compression)
            if len(data) < 40000:
                print(f"    [✖] Dropped {filename[:8]} (Low quality/size: {len(data)/1024:.1f}KB)", flush=True)
                return False
                
            # 2. Resolution Quality Gate (Reject < 600px on either side to allow web-portraits)
            try:
                import io
                from PIL import Image
                with Image.open(io.BytesIO(data)) as img:
                    if img.width < 600 or img.height < 600:
                        print(f"    [✖] Dropped {filename[:8]} (Low resolution: {img.width}x{img.height})", flush=True)
                        return False
            except:
                pass
                
            if self._is_pixel_duplicate(data):
                return False
                        
            category = self.modes[0]
            result_tags = ""
            if self.use_filter and self.img_filter:
                print(f"    [⚡] Neural scan initiated: {filename[:8]}...", flush=True)
                result = await asyncio.to_thread(self.img_filter.evaluate_image, data)
                is_accepted = result.get("is_accepted", False)
                reasoning = result.get("reasoning", "No reasoning provided.")
                category = result.get("category", category)
                result_tags = result.get("tags", "")
                
                # --- RAM CACHE STRATEGY (Temporary Garbage Collection) ---
                ram_cache_dir = os.path.join(self.root_dir, "ram_cache")
                os.makedirs(ram_cache_dir, exist_ok=True)
                ram_filename = f"{filename[:8]}_acc.jpg" if is_accepted else f"{filename[:8]}_rej.jpg"
                ram_filepath = os.path.join(ram_cache_dir, ram_filename)
                
                try:
                    with open(ram_filepath, 'wb') as rf: rf.write(data)
                    import datetime, json
                    ram_entry = {
                        "timestamp": datetime.datetime.now().isoformat(),
                        "hash": filename[:8], "filename": ram_filename,
                        "is_accepted": is_accepted, "reasoning": reasoning,
                        "source_url": url, "assigned_category": category
                    }
                    with open(os.path.join(self.root_dir, "session_ram.jsonl"), 'a') as rf:
                        rf.write(json.dumps(ram_entry) + "\n")
                        
                    ram_files = [os.path.join(ram_cache_dir, f) for f in os.listdir(ram_cache_dir)]
                    if len(ram_files) > 150:
                        ram_files.sort(key=os.path.getmtime)
                        for old_f in ram_files[:-100]: os.remove(old_f)
                except Exception as e:
                    print(f"[-] RAM CACHE FAILURE: {e}")
                # --- END RAM CACHE ---

                if not is_accepted:
                    print(f"    [✖] Neural evaluation rejected: {filename[:8]}", flush=True)
                    return False
                
            # Backup sanitization in case Gemini hallucinated a category string out of bounds
            if category not in self.modes and not (category == "vintage-ad" and "vintage-editorial" in self.modes):
                category = self.modes[0]

            folder_name = self.dir_mapping.get(category, category.capitalize())
            out_folder = os.path.join(self.base_dir, folder_name)
            filepath = os.path.join(out_folder, filename)

            if os.path.exists(filepath):
                return False

            import io
            from PIL import Image
            try:
                with Image.open(io.BytesIO(data)) as img:
                    exif_description = f"Publisher: {publication_name} | Source: {page_url} | Category: {category.upper()} | Tags: {result_tags}"
                    
                    # Pillow EXIF injection (Tag 270 = ImageDescription)
                    exif = img.getexif()
                    exif[270] = exif_description
                    
                    if img.format == 'PNG':
                        from PIL.PngImagePlugin import PngInfo
                        metadata = PngInfo()
                        metadata.add_text("Description", exif_description)
                        img.save(filepath, "PNG", pnginfo=metadata)
                    elif img.format in ['JPEG', 'WEBP', 'JPEG2000']:
                        if img.mode in ("RGBA", "P") and img.format == "JPEG":
                            img = img.convert("RGB")
                        img.save(filepath, img.format, exif=exif)
                    else:
                        with open(filepath, 'wb') as f:
                            f.write(data)
            except Exception as exif_e:
                print(f"    [!] EXIF Injection Failed ({exif_e}). Falling back to raw sweep.", flush=True)
                with open(filepath, 'wb') as f:
                    f.write(data)
                
            meta_entry = {
                "filename": filename,
                "publication": publication_name,
                "source_url": page_url,
                "cdn_url": url,
                "assigned_category": category
            }
            meta_file = os.path.join(self.root_dir, "metadata_global.jsonl")
            with open(meta_file, 'a') as mf:
                mf.write(json.dumps(meta_entry) + "\n")
                
            print(f"    [+] Asset Acquired [{category.upper()}]: {filepath}", flush=True)
            return True
        except Exception as e:
            print(f"    [-] Network error {url[:20]}: {e}", flush=True)
            
        return False

    async def download_batch(self, images: list, publication_name: str, concurrency: int = 10):
        print(f"[*] Starting download of {len(images)} images for {publication_name}...", flush=True)
        headers = {"User-Agent": "Mozilla/5.0"}
        successes = 0
        consecutive_rejects = 0

        connector = aiohttp.TCPConnector(limit=concurrency)
        async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
            semaphore = asyncio.Semaphore(concurrency)
            async def sem_task(img_d):
                async with semaphore:
                    return await self.download_image(session, img_d, publication_name)
            
            tasks = set()
            for img in images:
                if consecutive_rejects >= 35 and "vintage-editorial" not in self.modes:
                    print(f"    [!] MACRO-PATIENCE PROTOCOL: 35 consecutive AI rejections. Bailing on remaining {len(images)} assets on this page.", flush=True)
                    break
                    
                task = asyncio.create_task(sem_task(img))
                tasks.add(task)
                
                while len(tasks) >= concurrency:
                    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                    tasks = pending
                    for d in done:
                        try:
                            if d.result() is True:
                                successes += 1
                                consecutive_rejects = 0
                            else:
                                consecutive_rejects += 1
                        except:
                            consecutive_rejects += 1
                            
            if tasks:
                for d in await asyncio.gather(*tasks, return_exceptions=True):
                    if d is True: successes += 1
                    
        print(f"[*] Downloaded {successes} new images for {publication_name}.")
        return successes
