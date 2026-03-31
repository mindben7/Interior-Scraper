import os
import json
import io
import asyncio
from PIL import Image
from google.genai import types
from src.api_rotator import get_current_client, rotate_to_next_key

class GeometryTagger:
    def __init__(self, db_path):
        self.db_path = db_path
        self.model = 'gemini-2.5-flash'
        self.processed_files = set()
        
        if os.path.exists(self.db_path):
            with open(self.db_path, 'r') as f:
                for line in f:
                    if line.strip():
                        try:
                            data = json.loads(line)
                            self.processed_files.add(data.get('filepath'))
                        except: pass
                        
        self.system_instruction = """
        You are a rigid, deeply analytical architectural optical structuring engine.
        Your sole task is to analyze the spatial framing, optical geometry, and structural weight of the provided image.
        Provide a valid JSON response strictly utilizing the following schema structure:
        
        {
            "perspective": "<1-point, 2-point, flat_elevation, macro_detail, or complex_multi>",
            "anchor_subject": "<a 1-3 word generic classification of the main object, e.g., 'bed', 'vanity', 'sofa', 'table', 'pendant', 'chair'>",
            "composition": "<symmetric_center, left_heavy, right_heavy, or asymmetrical>",
            "lens_estimation": "<wide_angle, standard_50mm, telephoto_compression, or macro>",
            "optical_density_score": <int 1-10, 1 being stark empty minimalist space, 10 being heavily cluttered maximalist room>,
            "material_tactility": "<choose ONE of: soft_plush, textured_fabric, raw_wood, polished_stone, hard_concrete, or reflective_glass_metal>",
            "dominant_color_hex": "<the single primary background color hex code, e.g., '#F3E5AB'>",
            "subject_coords": {"x": <float 0.0-1.0 center of subject width>, "y": <float 0.0-1.0 center of subject height>}
        }
        
        Analyze the exact structural wireframe of the image. Do not inject aesthetic opinions. Output only the purely mechanical parsed JSON constraints.
        """

    def process_image(self, filepath):
        try:
            with Image.open(filepath) as img:
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                img.thumbnail((768, 768), Image.Resampling.LANCZOS)
                out_io = io.BytesIO()
                img.save(out_io, format="JPEG", quality=80)
                eval_bytes = out_io.getvalue()
        except Exception as e:
            print(f"[-] Image load/compression failed for {filepath}: {e}")
            return None
                
        client = get_current_client()
        
        try:
            response = client.models.generate_content(
                model=self.model,
                contents=[
                    types.Part.from_bytes(data=eval_bytes, mime_type='image/jpeg'),
                    "Analyze the spatial structure and output valid JSON."
                ],
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=0.0,
                    response_mime_type="application/json",
                )
            )
            
            data = json.loads(response.text.strip())
            data['filepath'] = filepath
            return data
            
        except Exception as e:
            error_str = str(e).lower()
            if 'quota' in error_str or '429' in error_str or 'exhausted' in error_str or 'billing' in error_str:
                print(f"[!] API Key exhausted. Rotating sequence...")
                rotate_to_next_key()
            else:
                pass
            return None

async def sweep_directory(target_dir, db_path):
    print(f"[*] Booting Structural Geometry Tagger on target volume: {target_dir}")
    tagger = GeometryTagger(db_path)
    
    supported_exts = ('.jpg', '.jpeg', '.png', '.webp')
    image_paths = []
    
    for root, _, files in os.walk(target_dir):
        for f in files:
            if f.lower().endswith(supported_exts):
                full_path = os.path.join(root, f)
                if full_path not in tagger.processed_files:
                    image_paths.append(full_path)
                    
    print(f"[*] Scan complete. Found {len(image_paths)} unprocessed frames requiring structural inference.")
    
    for i, path in enumerate(image_paths, 1):
        print(f"    --> [{i}/{len(image_paths)}] Optical Analysis: {os.path.basename(path)[:30]}...")
        result = await asyncio.to_thread(tagger.process_image, path)
        
        if result:
            with open(tagger.db_path, "a") as f:
                f.write(json.dumps(result) + "\n")
            print(f"        [+] {result.get('perspective', 'N/A')} | Anchor: {result.get('anchor_subject', 'N/A')} | Comp: {result.get('composition', 'N/A')}")
            
    print(f"[*] Structural tagging sweep sequence complete.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Optical Geometry Structural Engine")
    parser.add_argument('--dir', type=str, required=True, help="Target directory to recursively sweep")
    parser.add_argument('--db', type=str, default="data/structural_manifest.jsonl", help="Path to save metadata db")
    args = parser.parse_args()
    
    asyncio.run(sweep_directory(args.dir, args.db))
