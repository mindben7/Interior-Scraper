import os
import json
import xml.etree.ElementTree as ET

def hex_to_hsv(hexStr):
    try:
        hexStr = hexStr.lstrip('#')
        r, g, b = tuple(int(hexStr[i:i+2], 16) for i in (0, 2, 4))
        import colorsys
        h, s, v = colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)
        return h, s, v
    except: return (0, 0, 0)

def create_montage_fcpxml(data_list, output_file, concept="match-cut", fps=24, frame_duration=4, zoom_start=1.0, zoom_end=1.3):
    if not data_list:
        print("[-] No images provided for montage generation.")
        return
        
    print(f"[*] Compiling {len(data_list)} mathematically-matched frames ({concept}) into DaVinci Resolve FCPXML...")
    
    total_duration_frames = len(data_list) * frame_duration
    
    fcpxml = ET.Element("fcpxml", version="1.9")
    resources = ET.SubElement(fcpxml, "resources")
    
    format_id = "r1"
    width, height = 1920, 1080
    ET.SubElement(resources, "format", id=format_id, name="FFVideoFormat1080p24", frameDuration="100/2400s", width=str(width), height=str(height))
    
    for i, data in enumerate(data_list):
        path = data.get("filepath", "")
        ET.SubElement(resources, "asset", id=f"asset_{i}", name=os.path.basename(path), src=f"file://{path}")
        
    library = ET.SubElement(fcpxml, "library")
    event = ET.SubElement(library, "event", name="Optic Montage Engine")
    project = ET.SubElement(event, "project", name=f"Sequence - {concept.upper()}")
    sequence = ET.SubElement(project, "sequence", format=format_id, duration=f"{total_duration_frames*100}/2400s")
    spine = ET.SubElement(sequence, "spine")
    
    scale_range = zoom_end - zoom_start
    pan_trajectory = 400.0 # pixels to move across infinite pan
    
    for i, data in enumerate(data_list):
        img_path = data.get("filepath", "")
        progress = i / max(1, (len(data_list) - 1))
        
        clip_start = i * frame_duration
        clip = ET.SubElement(spine, "asset-clip", name=os.path.basename(img_path), ref=f"asset_{i}", offset=f"{clip_start*100}/2400s", duration=f"{frame_duration*100}/2400s", start="0s")
        
        # Apply mathematical transforms depending on the geometric concept
        if concept == "infinite-pan":
            current_x = -200 + (progress * pan_trajectory)
            ET.SubElement(clip, "adjust-transform", position=f"{current_x:.4f} 0.0000", scale="1.1 1.1")
            
        elif concept == "subject-lock":
            coords = data.get("subject_coords", {"x": 0.5, "y": 0.5})
            # To move subject from X to center, offset image by (0.5 - X)
            off_x = (0.5 - coords.get("x", 0.5)) * width
            off_y = (0.5 - coords.get("y", 0.5)) * -height
            ET.SubElement(clip, "adjust-transform", position=f"{off_x:.4f} {off_y:.4f}", scale="1.2 1.2")
            
        else: # match-cut, density-ramp, color-topo, material-evo
            current_scale = zoom_start + (scale_range * progress)
            ET.SubElement(clip, "adjust-transform", scale=f"{current_scale:.4f} {current_scale:.4f}")
            
    tree = ET.ElementTree(fcpxml)
    tree.write(output_file, encoding="utf-8", xml_declaration=True)
    print(f"[+] Successfully generated conceptual sequence timeline at: {output_file}")


def generate_montage(db_path, output_xml, concept="match-cut", target_anchor=None, target_perspective=None, limit=30):
    if not os.path.exists(db_path):
        print(f"[-] Structural manifest not found at {db_path}")
        return
        
    raw_data = []
    try:
        with open(db_path, 'r') as f:
            for line in f:
                if not line.strip(): continue
                data = json.loads(line)
                
                if target_anchor and target_anchor.lower() not in data.get("anchor_subject", "").lower():
                    continue
                if target_perspective and target_perspective.lower() not in data.get("perspective", "").lower():
                    continue
                    
                path = data.get("filepath", "")
                if os.path.exists(path):
                    raw_data.append(data)
    except Exception as e:
        print(f"[-] Database read error: {e}")
        return
        
    print(f"[*] Filtering logic matched {len(raw_data)} structural frames. Sorting arrays via '{concept}' constraint algorithm...")
    
    # Mathematical Array Sorting
    if concept == "density-ramp":
        # Sort purely by optical density integer (minimal -> maximal)
        raw_data.sort(key=lambda d: d.get("optical_density_score", 5))
        
    elif concept == "color-topo":
        # Sort by HSV color space values extracted from Hex properties
        def get_hsv(d): return hex_to_hsv(d.get("dominant_color_hex", "#000000"))
        raw_data.sort(key=lambda d: (get_hsv(d)[0], get_hsv(d)[1], get_hsv(d)[2]))
        
    elif concept == "material-evo":
        # Lexical map ranking softness to hardness
        m_map = {"soft_plush": 1, "textured_fabric": 2, "raw_wood": 3, "polished_stone": 4, "hard_concrete": 5, "reflective_glass_metal": 6}
        raw_data.sort(key=lambda d: m_map.get(d.get("material_tactility", ""), 0))
        
    # Standard match-cuts (or randomly grouped ones) don't need explicit sequential sorting
    
    valid_data = raw_data[:limit]
    if len(valid_data) >= 5: # bare minimum frames
        create_montage_fcpxml(valid_data, output_xml, concept=concept)
    else:
        print("[-] Aborted: Not enough identical frames matched the criteria matrix.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Geometric Match-Cut Montage Generator")
    parser.add_argument('--db', type=str, default="/Users/ben/.gemini/antigravity/playground/ghost-spirit/data/structural_manifest.jsonl", help="Path to structural DB")
    parser.add_argument('--out', type=str, default="/Users/ben/Desktop/MatchCutSequence.fcpxml", help="Output sequence path")
    parser.add_argument('--concept', type=str, default="match-cut", help="Montage conceptual algebraic logic")
    parser.add_argument('--anchor', type=str, default=None, help="Filter by anchor subject (e.g. 'bed')")
    parser.add_argument('--perspective', type=str, default=None, help="Filter by perspective (e.g. '1-point')")
    parser.add_argument('--limit', type=int, default=30, help="Max images in sequence")
    
    args = parser.parse_args()
    generate_montage(args.db, args.out, args.concept, args.anchor, args.perspective, args.limit)
