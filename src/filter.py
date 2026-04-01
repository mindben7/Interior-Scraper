import os
import json
from google import genai
from google.genai import types

class AgentFilter:
    def __init__(self, modes=None):
        self.modes = modes or ["wide"]
        self.model = 'gemini-2.5-flash'
        
        mode_rules = {
            "wide": "wide: General wide establishing shots of architectural interior spaces showing full room layouts. MUST be extremely high quality real photography. Absolutely NO humans/people allowed in the frame. NO cheap commercial spaces (like local community centers, gyms, or basic public pools).",
            "detail": "detail: High-end 85mm+ shallow depth-of-field vignettes, texture macros, styling details. NOT a full room. Absolutely NO humans/people.",
            "lighting": "lighting: Exclusively ultra-luxury, bespoke, and high-end architectural designer lighting fixtures (avant-garde pendants, sculptural sconces, massive chandeliers). Must be shot with high-end professional photography framing.",
            "mood": "mood: Abstract, surreal, highly artistic design inspiration. Can be bold, conceptual art, cover-style graphic photography, or avant-garde materials. MUST be highly aesthetic, inspiring, and design-forward. Can include non-traditional objects.",
            "restaurant": "restaurant: Exclusively ultra-luxury, high-end restaurant, bar, and hospitality interiors. Must be shot by professional architectural photographers. Can be wides or details of dining spaces, bar counters, or lounge areas. Absolutely NO cheap diners, fast food, or low-quality commercial cafeteria spaces."
        }
        
        rules_text = "\n".join(f"- {m}" for k, m in mode_rules.items() if k in self.modes)
        
        if any(m.lower() in ["preset-contemporary", "preset-architects"] for m in self.modes):
            bias_title = "THE CONTEMPORARY MASTER PROTOCOL"
            bias_content = ("You are evaluating imagery for a specific client hunting for the world's most elite contemporary and minimalist interior architecture. You MUST aggressively seek out and ONLY ACCEPT images that exhibit this exact aesthetic:\n"
                            "- THE VIBE: Ultra-luxury tailored contemporary, moody architectural spaces, and highly textured minimalism.\n"
                            "- THE STYLE: Italian modernism, gallery-level artisan craftsmanship, dark moody woods, burnished brass/bronze, and low-slung tailored silhouettes in the exact vein of Minotti, Henge, Studio Liaigre, Cassina, and Piet Boon.\n"
                            "- THE WEALTH: Restrained, incredibly sophisticated $20,000,000+ bespoke residences relying on noble raw materials, heavy stone, and flawless architectural lighting.\n"
                            "RUTHLESSLY REJECT any bright preppy spaces, colorful maximalism (Kelly Wearstler style), traditional classicism, rustic farmhouses, or cheap generic stark 1990s modernism.\n"
                            "CRITICAL BAN: You MUST RUTHLESSLY REJECT isolated furniture pieces on solid white, grey, or transparent backgrounds (e-commerce catalog shots). We ONLY accept fully styled, moody, environmental ROOM shots.")
        else:
            bias_title = "THE UNYIELDING CLIENT DNA PROTOCOL"
            bias_content = ("You are evaluating imagery for a specific client focused on South Florida, Miami, and global $10M+ ultra-luxury real estate. You MUST aggressively seek out and ONLY ACCEPT images that exhibit this specific aesthetic:\n"
                            "- THE VIBE: 'Boutique-hotel-style residential' and 'highly refined, upscale commercial'.\n"
                            "- THE STYLE: Kelly Wearstler Neoclassical glamour, Philippe Starck & Marcel Wanders maximalism, and Miami Art Deco.\n"
                            "- THE WEALTH: Extremely bespoke, highly tailored $10,000,000+ private residences and high-rise luxury hotels.\n"
                            "RUTHLESSLY REJECT any space that looks like sparse/budget modernism, rustic cabins, generic corporate offices, or anything that lacks this specific 'ultra-refined boutique hotel' DNA, even if it is beautifully photographed.")

        self.system_instruction = f"""
        You are an elite architectural photography curator acting as an automated tagging pipeline for ultra-luxury design.
        
        Evaluate the provided photograph against the following active target categories:
        {rules_text}
        
        If the image solidly matches ANY of the active categories above AND it passes all the Universal Bans below, you must aggressively bias toward ACCEPTING IT. Do not reject images simply because of minor styling flaws if the core architecture/design accurately represents the category. We want a high volume of beautiful design inspiration.
        
        CRITICAL AESTHETIC BIAS - {bias_title}:
        {bias_content}
        
        UNIVERSAL BANS (CRITICAL OVERRIDE):
        You MUST RUTHLESSLY REJECT the image if it triggers ANY of the following rules, regardless of how well it matches the category:
        1. VETO TEXT & TYPOGRAPHY: Absolutely NO text, typography, writing, watermarks, corporate logos, UI elements, or magazine article layouts. If the image is a screenshot of a webpage with text above/below the photo, you MUST REJECT IT. Photography only.
        2. VETO 3D/CGI & POOR RENDERS: Absolutely NO 3D renders, CGI, architectural visualizations (ArchViz), or AI-generated outputs. Be EXTREMELY vigilant against "poor quality, really bare" renderings. The image MUST be 100% authentic, high-quality, optical photography with real-world organic imperfections, authentic lighting depth, and high-quality textures. Any sterile, empty 3D room renders must be instantly rejected.
        3. VETO HUMANS: Absolutely NO humans, people, limbs, hands, or digital avatars anywhere in the frame for 'wide' and 'detail' shots.
        4. VETO CHEAP COMMERCIAL: Reject gritty, corny, or low-budget commercial spaces like basic gym swimming pools, corporate cafeterias, or generic hardware catalogs. We ONLY accept elite, ultra-luxury, Architectural Digest-level residential or boutique hospitality spaces.
        5. VETO LOW QUALITY: Reject blurry, low-resolution, or heavily compounded JPEG artifacts.
        
        JSON SCHEMA RESPONSE:
        You must return a valid JSON object representing your decision.
        If the image is completely irrelevant to the active categories or triggers ANY of the UNIVERSAL BANS, return exactly:
        {{"is_accepted": false}}
        
        If the image solidly matches an active category AND passes all strict quality bans, select the SINGLE BEST MATCHING category string, summarize its contents in a visually-rich 1-sentence comma separated list of design keywords (like materials, style, lighting), and return exactly:
        {{"is_accepted": true, "category": "<exact category string>", "tags": "minimalist, brutalist, concrete floor, brass pendant"}}
        """

    def evaluate_image(self, image_bytes: bytes) -> dict:
        try:
            import io
            from PIL import Image
            
            try:
                with Image.open(io.BytesIO(image_bytes)) as img:
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    img.thumbnail((768, 768), Image.Resampling.LANCZOS)
                    out_io = io.BytesIO()
                    img.save(out_io, format="JPEG", quality=80)
                    eval_bytes = out_io.getvalue()
            except Exception as compress_err:
                print(f"        [!] Pillow compression failing: {compress_err}")
                print(f"        [✖] Asset byte-stream is profoundly corrupt or unsupported. Bailing out before API matrix.")
                return {"is_accepted": False, "category": "corrupted_bytes", "tags": "", "reasoning": f"Asset downloaded as corrupt or unsupported byte-stream: {str(compress_err)}"}
                
            try:
                v_p = "/Users/ben/.gemini/antigravity/playground/ghost-spirit/static/vision_agent.jpg"
                with open(v_p, "wb") as vf: vf.write(eval_bytes)
                with open(v_p + ".status", "w") as sf: sf.write("EVALUATING")
            except: pass
                
            from src.api_rotator import get_current_client
            dynamic_client = get_current_client()
            
            contents = []
            
            # --- BIDIRECTIONAL ACTIVE LEARNING ---
            base_dir = "/Volumes/BT4TB/_CLIENTS/Ruby/All Ruby Projects/Interior Designer Inspiration"
            if not os.path.exists(base_dir): base_dir = "/Users/ben/.gemini/antigravity/playground/ghost-spirit/data"
            ram_dir = os.path.join(base_dir, "ram_cache")
            
            try:
                pos_file = os.path.join(base_dir, "positive_overrides.txt")
                if os.path.exists(pos_file):
                    with open(pos_file, 'r') as f: pos_hashes = [l.strip() for l in f.readlines() if l.strip()][-6:]
                    if pos_hashes:
                        contents.append("CRITICAL SESSION CONTEXT: The user manually RESTORED these images after you erroneously rejected them. You MUST explicitly expand your aesthetic acceptance baseline to include imagery resembling these examples:")
                        for h in pos_hashes:
                            p = os.path.join(ram_dir, f"{h}_acc.jpg")
                            if os.path.exists(p):
                                with open(p, 'rb') as vf: contents.append(types.Part.from_bytes(data=vf.read(), mime_type='image/jpeg'))
                                
                neg_file = os.path.join(base_dir, "negative_overrides.txt")
                if os.path.exists(neg_file):
                    with open(neg_file, 'r') as f: neg_hashes = [l.strip() for l in f.readlines() if l.strip()][-6:]
                    if neg_hashes:
                        contents.append("CRITICAL SESSION CONTEXT: The user manually DELETED these images after you mistakenly accepted them. You MUST explicitly heavily penalize and REJECT any target imagery functionally resembling these negative examples:")
                        for h in neg_hashes:
                            p = os.path.join(ram_dir, f"{h}_rej.jpg")
                            if os.path.exists(p):
                                with open(p, 'rb') as vf: contents.append(types.Part.from_bytes(data=vf.read(), mime_type='image/jpeg'))
            except Exception as active_learn_err:
                print(f"[-] Active learning load failure: {active_learn_err}")
            # --- END BIDIRECTIONAL LEARNING ---
                            
            contents.append("Below is the TARGET image for you to evaluate against your system instructions and the user override patterns above. Output valid JSON:")
            contents.append(types.Part.from_bytes(data=eval_bytes, mime_type='image/jpeg'))
            
            import time
            max_retries = 6
            response = None
            
            for attempt in range(max_retries):
                try:
                    response = dynamic_client.models.generate_content(
                        model=self.model,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            system_instruction=self.system_instruction,
                            temperature=0.0,
                            response_mime_type="application/json",
                        )
                    )
                    break  # Success, exit retry loop
                except Exception as api_e:
                    error_str = str(api_e).lower()
                    if '503' in error_str or 'unavailable' in error_str or '429' in error_str or 'quota' in error_str or 'exhausted' in error_str:
                        if attempt < max_retries - 1:
                            sleep_time = (2 ** attempt) + 2  # 3s, 4s, 6s, 10s...
                            print(f"        [⚠] API Capacity/Quota Hit (Attempt {attempt+1}/{max_retries}). Backing off {sleep_time}s...", flush=True)
                            
                            if 'quota' in error_str or 'exhausted' in error_str or '429' in error_str:
                                from src.api_rotator import rotate_to_next_key, get_current_client
                                rotate_to_next_key()
                                dynamic_client = get_current_client()
                                
                            time.sleep(sleep_time)
                            continue
                    
                    # If not retryable or out of retries, print and fail silently
                    print(f"        [!] Fatal API Error evaluating image: {api_e}", flush=True)
                    return {"is_accepted": False}
                    
            if response is None:
                return {"is_accepted": False}
            
            try:
                data = json.loads(response.text.strip())
            except:
                data = {"is_accepted": False}
                
            try:
                with open("/Users/ben/.gemini/antigravity/playground/ghost-spirit/static/vision_agent.jpg.status", "w") as sf:
                    sf.write("ACCEPTED" if data.get("is_accepted") else "REJECTED")
            except: pass
            
            return data
            
        except Exception as e:
            print(f"        [!] Global Error evaluating image: {e}", flush=True)
            return {"is_accepted": False}
