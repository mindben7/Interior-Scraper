import os
import glob
import json
from PIL import Image, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True

ROOT_DIR = "/Volumes/BT4TB/_CLIENTS/Ruby/All Ruby Projects/Interior Designer Inspiration/Images"

def get_dhash(img_path):
    try:
        with Image.open(img_path) as img:
            img = img.convert('L').resize((9, 8), Image.Resampling.LANCZOS)
            diff = []
            for row in range(8):
                for col in range(8):
                    pixel_left = img.getpixel((col, row))
                    pixel_right = img.getpixel((col + 1, row))
                    diff.append(pixel_left > pixel_right)
            hash_num = 0
            for i, bit in enumerate(diff):
                if bit: hash_num |= (1 << i)
            return format(hash_num, '016x')
    except Exception as e:
        print(f"Error hashing {img_path}: {e}")
        return None

def clean_folder(subfolder_name):
    folder_path = os.path.join(ROOT_DIR, subfolder_name)
    if not os.path.exists(folder_path):
        print(f"Folder not found: {folder_path}")
        return
        
    print(f"\n[*] Scanning {subfolder_name} for duplicates...")
    image_files = glob.glob(os.path.join(folder_path, "*.jpg"))
    # Sort files so we always keep the 'oldest' or first one deterministically
    image_files.sort()
    
    seen_hashes = set()
    deleted_count = 0
    valid_files = set()
    
    for img_path in image_files:
        dhash = get_dhash(img_path)
        if not dhash:
            continue
            
        if dhash in seen_hashes:
            os.remove(img_path)
            deleted_count += 1
            print(f"    [X] DELETED CLONE: {os.path.basename(img_path)}")
        else:
            seen_hashes.add(dhash)
            valid_files.add(os.path.basename(img_path))
            
    print(f"[*] {subfolder_name}: Eradicated {deleted_count} duplicate image files.")
    
    # Clean up metadata.jsonl
    metadata_path = os.path.join(folder_path, "metadata.jsonl")
    if os.path.exists(metadata_path):
        valid_lines = []
        purged_lines = 0
        with open(metadata_path, 'r') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    # Use os.path.basename to just match the core file regardless of relative tracking
                    fn = os.path.basename(data.get("filename", ""))
                    if fn in valid_files:
                        valid_lines.append(line)
                    else:
                        purged_lines += 1
                except: pass
                
        with open(metadata_path, 'w') as f:
            for line in valid_lines:
                f.write(line)
                
        print(f"[*] {subfolder_name}: Purged {purged_lines} orphaned entries from metadata.jsonl.")

if __name__ == "__main__":
    print("=============================================")
    print("      GLOBAL DUPLICATE ERADICATOR            ")
    print("=============================================")
    clean_folder("General")
    clean_folder("Details")
    clean_folder("Materials")
    print("\n[+] Total System Scan Complete.")
