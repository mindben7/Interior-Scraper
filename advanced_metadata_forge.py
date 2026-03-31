import os
import json
import asyncio
import subprocess
import sys

sys.stdout.reconfigure(line_buffering=True)
sys.path.append("/Users/ben/.gemini/antigravity/playground/ghost-spirit")
from src.api_rotator import get_current_client
from google.genai import types

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

async def analyze_image_deep(filepath):
    try:
        from PIL import Image
        import io
        with Image.open(filepath) as img:
            if img.mode != 'RGB': img = img.convert('RGB')
            img.thumbnail((768, 768), Image.Resampling.LANCZOS)
            out = io.BytesIO()
            img.save(out, format="JPEG", quality=80)
            img_bytes = out.getvalue()
    except Exception as e:
        print(f"[-] Image Error {filepath}: {e}")
        return None
        
    client = get_current_client()
    system_instruction = """
    You are an elite architectural photography analyst.
    Analyze this interior design asset and extract precise attributes.
    1. "genre": A precise 2-4 word string identifying the architectural/interior style (e.g., "Scandinavian Minimalist", "Mid-Century Modern", "Industrial Brutalist").
    2. "designer": If the designer, architect, or firm is extremely obvious, name them. Otherwise output "Unknown Designer".
    3. "colors": Array of 2-4 exact color or material strings (e.g., ["Teal Blue", "Walnut", "Matte Black"]).
    4. "tags": Array of 3-5 specific objects/fixtures visible in the frame (e.g., ["boucle sofa", "brass pendant", "herringbone floor"]).
    
    You must output strictly JSON: {"genre": "...", "designer": "...", "colors": ["..."], "tags": ["..."]}
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[types.Part.from_bytes(data=img_bytes, mime_type='image/jpeg'), "Analyze this space."],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.0,
                response_mime_type="application/json",
            )
        )
        return json.loads(response.text.strip())
    except Exception as e:
        error_str = str(e).lower()
        if 'quota' in error_str or '429' in error_str:
            print(f"        [!] API EXHAUSTED: {e}")
            from src.api_rotator import rotate_to_next_key
            rotate_to_next_key()
        return None

def force_inject_macos_metadata(filepath, ai_data, url):
    genre = ai_data.get('genre', 'Interior Design')
    designer = ai_data.get('designer', 'Unknown Studio')
    colors = ai_data.get('colors', [])
    tags = ai_data.get('tags', [])
    
    all_tags = colors + tags
    
    cmd = [
        "exiftool", 
        "-overwrite_original",
        f"-EXIF:ImageDescription={genre}",
        f"-XMP:Description={genre}",
        f"-XMP:Creator={designer}",
        f"-EXIF:Artist={designer}",
        f"-MDItemWhereFroms={url}"
    ]
    
    # Map array to ExifTool lists for MacOS Extended Attributes & XMP Subjects
    for t in all_tags:
        clean_t = str(t).replace('"', '').replace(',', '')
        cmd.append(f"-MDItemUserTags={clean_t}")
        cmd.append(f"-XMP:Subject={clean_t}")
        
    cmd.append(filepath)
    
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except Exception as e:
        print(f"[-] Exiftool Error on {filepath}: {e}")

async def main():
    print("[*] INITIALIZING ADVANCED BPLIST FORGE WORKER")
    meta_db = load_global_metadata()
    
    target_modes = ["images_wide", "images_detail", "images_lighting", "images_millwork"]
    base_target = "/Volumes/BT4TB/_CLIENTS/Ruby/All Ruby Projects/Interior Designer Inspiration"
    
    for mode in target_modes:
        folder = os.path.join(base_target, mode)
        if not os.path.exists(folder): continue
        
        print(f"\n[*] Sweeping: {folder}")
        files = [f for f in os.listdir(folder) if f.lower().endswith(('.jpg', '.webp', '.png'))]
        
        for file in files:
            filepath = os.path.join(folder, file)
            
            # Check if MDItemWhereFroms is already injected using naive command
            try:
                check = subprocess.run(["xattr", "-p", "com.apple.metadata:kMDItemWhereFroms", filepath], capture_output=True, text=True)
                if check.returncode == 0:
                    continue # Already processed
            except: pass
                
            entry = meta_db.get(file, {})
            source_url = entry.get('source_url', 'https://ghost-spirit.local')
            
            print(f"    [>] Analyzing Geometry {file[:15]}...")
            ai_data = await analyze_image_deep(filepath)
            
            if ai_data:
                print(f"        [+] Forging Apple BPLIST -> Genre: {ai_data.get('genre')} | Author: {ai_data.get('designer')} | Tags: {len(ai_data.get('tags', []))}")
                force_inject_macos_metadata(filepath, ai_data, source_url)
                
            await asyncio.sleep(1.5)

if __name__ == "__main__":
    asyncio.run(main())
