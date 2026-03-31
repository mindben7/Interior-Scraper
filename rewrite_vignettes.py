import re

with open('infinite_vignettes.py', 'r') as f:
    code = f.read()
code = code.replace('from src.downloader import ImageDownloader', 'from src.vignette_downloader import VignetteDownloader')
code = code.replace('ImageDownloader(output_dir=output_dir, use_filter=True)', 'VignetteDownloader(use_filter=True)')
code = code.replace("config_path = 'config/master_publications.yaml'", "config_path = 'config/interior_designers.yaml'")
code = code.replace('visited_file = "visited.txt"', 'visited_file = "vignettes_visited.txt"')
code = code.replace('swept_file = "swept.txt"', 'swept_file = "vignettes_swept.txt"')
with open('infinite_vignettes.py', 'w') as f: f.write(code)

with open('src/vignette_downloader.py', 'r') as f:
    code = f.read()
code = code.replace('class ImageDownloader:', 'class VignetteDownloader:')
code = code.replace('from src.filter import ImageFilter', 'from src.vignette_filter import VignetteFilter')
code = code.replace('self.img_filter = ImageFilter()', 'self.img_filter = VignetteFilter()')
code = code.replace('def __init__(self, output_dir="data/images", use_filter=True):', 'def __init__(self, output_dir="/Volumes/BT4TB/_CLIENTS/Ruby/All Ruby Projects/Interior Designer Inspiration/Images/Details", use_filter=True):')
with open('src/vignette_downloader.py', 'w') as f: f.write(code)

with open('src/vignette_filter.py', 'r') as f:
    code = f.read()
code = code.replace('class ImageFilter:', 'class VignetteFilter:')
# Replace system instruction block using regex
import re
new_prompt = '''        self.system_instruction = """
        You are a master interior design curator. Your ONLY mission is to find interior vignettes, detail shots, material studies, and texture macros.
        You MUST completely REJECT wide, establishing shots that show the entire room or full floorplan.
        Stop using broad room terms. Do not accept "living room" or "kitchen" wide angles.
        
        The ONLY acceptable images will cleanly match one of these three exact stylistic descriptions:
        
        1. VIGNETTES: Tightly framed interior vignette, close up of decor/furniture, natural soft window light, photorealistic, 85mm lens, shallow depth of field, high-end editorial interior photography.
        2. MATERIAL & MACRO DETAILS: Macro photography of a material (ribbed glass, natural linen, travertine, plaster, wood grain), extreme close up, interior design material study, sharp focus on texture, soft diffused lighting.
        3. HARDWARE & FIXTURES: Architectural detail shot of an item (e.g., unlacquered brass faucet, custom joinery), interior detail photography, 100mm macro lens, cinematic lighting, photorealistic.
        
        Rate YES if the image perfectly matches one of the three descriptions above (tight focal length, shallow depth of field, vignette/macro). 
        Reject anything else. Answer with ONE WORD ONLY: either "YES" or "NO".
        """'''
code = re.sub(r'self\.system_instruction = """.*?"""', new_prompt.strip(), code, flags=re.DOTALL)
with open('src/vignette_filter.py', 'w') as f: f.write(code)

with open('dashboard.py', 'r') as f:
    code = f.read()
code = code.replace('"Interior Design Details": {"log": "details.log", "script": "infinite_details.py"},', '"Vignettes & Details": {"log": "vignette.log", "script": "infinite_vignettes.py"},')
with open('dashboard.py', 'w') as f: f.write(code)

print("Rewrite complete.")
