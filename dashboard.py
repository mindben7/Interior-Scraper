from flask import Flask, jsonify, render_template, request, send_file
import os
import time
import re
import sys
import atexit
import signal
from urllib.parse import urlparse

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
WORKSPACE = "/Users/ben/.gemini/antigravity/playground/ghost-spirit"

LOG_FILE = os.path.join(WORKSPACE, "data/agent.log")

def hard_kill_agent():
    print("\n[!] GLOBAL DEAD MAN'S SWITCH ENGAGED. Terminal shutting down.")
    os.system(f"pkill -9 -f 'agent.py --modes'")

atexit.register(hard_kill_agent)
signal.signal(signal.SIGTERM, lambda s, f: sys.exit(0))
signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))

def analyze_log_stats(all_lines):
    analyzed = 0; saved = 0
    current_domain = "SYSTEM STANDBY"
    for line in all_lines:
        if "Found " in line and (" images" in line or " potential" in line or " assets" in line):
            m = re.search(r'Found (\d+)', line)
            if m: analyzed += int(m.group(1))
        elif "[+] Asset Acquired" in line or "[+] SAVED" in line.upper():
            saved += 1
        elif "[*] Scanning" in line or "[*] Extracting images from" in line:
            urls = re.findall(r'https?://[^\s]+', line)
            if urls:
                try:
                    current_domain = urlparse(urls[0]).netloc.replace("www.", "").upper()
                except: pass
            
    ratio = "0.0%"
    if analyzed > 0: ratio = f"{(saved / analyzed) * 100:.1f}%"
    return {"analyzed": analyzed, "saved": saved, "ratio": ratio, "current_domain": current_domain}

@app.route("/")
def index():
    return render_template("index.html")

_odometer_cache = {"count": 0, "scanned": 22000, "last_check": 0}

def get_global_metrics():
    global _odometer_cache
    if time.time() - _odometer_cache["last_check"] < 5.0:
        return _odometer_cache["count"], _odometer_cache["scanned"]
        
    count = 0
    scanned = 22000
    paths = [
        os.path.join(WORKSPACE, "data"),
        "/Volumes/BT4TB/_CLIENTS/Ruby/All Ruby Projects/Interior Designer Inspiration"
    ]
    for p in paths:
        if os.path.exists(p):
            for root, dirs, files in os.walk(p):
                count += sum(1 for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')))
                
    paths_scan = [
        os.path.join(WORKSPACE, "data/scanned_global_tracker.txt"),
        "/Volumes/BT4TB/_CLIENTS/Ruby/All Ruby Projects/Interior Designer Inspiration/scanned_global_tracker.txt"
    ]
    for p in paths_scan:
        if os.path.exists(p):
            try:
                with open(p, 'r') as f:
                    for line in f:
                        if line.strip().isdigit():
                            scanned += int(line.strip())
            except: pass
            
    _odometer_cache["count"] = count
    _odometer_cache["scanned"] = scanned
    _odometer_cache["last_check"] = time.time()
    return count, scanned

@app.route("/api/logs")
def get_logs():
    if not os.path.exists(LOG_FILE):
        return jsonify({"lines": ["Awaiting System Initialization... Select Target Filters and press INITIATE."], "stats": {"analyzed": 0, "saved": 0, "ratio": "0.0%", "global_total": 0}, "total_lines": 0})
    try:
        with open(LOG_FILE, 'r') as f:
            all_lines = f.readlines()
            stats = analyze_log_stats(all_lines)
            
            global_count, global_scanned = get_global_metrics()
            stats["global_total"] = global_count
            stats["analyzed"] = global_scanned
            
            arr = [l.strip() for l in all_lines if l.strip()]
            return jsonify({"lines": arr[-150:], "stats": stats, "total_lines": len(arr)})
    except Exception as e:
        return jsonify({"lines": [f"Error reading log: {e}"], "stats": {"analyzed": 0, "saved": 0, "ratio": "0.0%"}, "total_lines": 0})

@app.route("/api/system/status")
def system_status():
    import subprocess
    cmd = f"ps aux | grep 'python.*{WORKSPACE}' | grep -v 'dashboard.py' | grep -v grep"
    running = False
    paused = False
    modes = []
    process_names = []
    try:
        output = subprocess.check_output(cmd, shell=True).decode('utf-8')
        for line in output.split('\n'):
            if line.strip():
                running = True
                cols = line.split()
                if len(cols) >= 8 and 'T' in cols[7]:
                    paused = True
                m = re.search(r'python[^\w]+.*?([\w_]+\.py)', line)
                if m and m.group(1).upper() not in process_names:
                    process_names.append(m.group(1).upper())
                
                m_mode = re.search(r'--modes\s+([^\s]+)', line)
                if m_mode:
                    for md in m_mode.group(1).split(','):
                        md = md.strip()
                        if md and md not in modes: modes.append(md)
    except:
        pass

    if process_names and "AGENT.PY" not in process_names:
        modes = process_names
        
    return jsonify({"active": running, "paused": paused, "modes": modes})

@app.route("/api/vision_status")
def vision_status():
    files = ["static/vision_agent.jpg"]
    newest = None; newest_mtime = 0; newest_status = "EVALUATING"
    
    for relative_f in files:
        path = os.path.join(WORKSPACE, relative_f)
        if os.path.exists(path):
            m = os.path.getmtime(path)
            if m > newest_mtime:
                newest_mtime = m
                newest = relative_f
                try:
                    with open(path + ".status", "r") as sf: newest_status = sf.read().strip()
                except: pass
                
    if newest:
        return jsonify({"status": newest_status, "mtime": newest_mtime, "img": f"/{newest}"})
    return jsonify({"status": "OFFLINE", "mtime": 0, "img": ""})

@app.route("/api/control/start/<modes_str>", methods=["POST"])
def start_agent(modes_str):
    os.system("ps aux | grep -v grep | grep 'agent.py --modes' | awk '{print $2}' | xargs kill -9")
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    try:
        with open(LOG_FILE, 'a') as f: f.write(f"\n\n[▶] INITIATING INTERIORS SCRAPER AGENT TARGETING {modes_str.upper()}\n")
    except: pass
    
    target_url = ""
    try:
        data = request.get_json(silent=True)
        if data and data.get("target_url"):
            target_url = data.get("target_url").strip()
    except: pass
    
    cmd_extras = ""
    if target_url:
        cmd_extras = f" --target-url '{target_url}'"
    
    if "preset-contemporary" in modes_str.lower() or "preset-architects" in modes_str.lower():
        try:
            with open(LOG_FILE, 'a') as f: f.write(f"\\n[⚡] SWARM ARCHITECTURE DETECTED. SCALING INTO 2 BACKGROUND THREADS...\\n")
        except: pass
        preset = "preset-architects" if "preset-architects" in modes_str.lower() else "preset-contemporary"
        os.system(f"cd {WORKSPACE} && nohup venv/bin/python swarm_manager.py 2 '{preset}' > /dev/null 2>&1 &")
    else:
        # Modes String comes in as "wide,detail,lighting"
        os.system(f"cd {WORKSPACE} && nohup venv/bin/python -u agent.py --modes {modes_str}{cmd_extras} >> {LOG_FILE} 2>&1 &")
        
    return jsonify({"status": "success", "modes": modes_str})

@app.route("/api/control/stop", methods=["POST"])
def stop_agent():
    os.system("ps aux | grep -v grep | grep 'agent.py --modes' | awk '{print $2}' | xargs kill -9")
    try:
        with open(LOG_FILE, 'a') as f: f.write("\n\n[■] AGENT ABORTED BY USER OVERRIDE\n")
    except: pass
    return jsonify({"status": "success"})

@app.route("/api/control/pause", methods=["POST"])
def pause_agent():
    os.system("ps aux | grep -v grep | grep 'agent.py --modes' | awk '{print $2}' | xargs kill -STOP")
    try:
        with open(LOG_FILE, 'a') as f: f.write("\n\n[⏸] AGENT SUSPENDED BY USER\n")
    except: pass
    return jsonify({"status": "success"})

@app.route("/api/control/resume", methods=["POST"])
def resume_agent():
    os.system("ps aux | grep -v grep | grep 'agent.py --modes' | awk '{print $2}' | xargs kill -CONT")
    try:
        with open(LOG_FILE, 'a') as f: f.write("\n\n[▶] AGENT RESUMED\n")
    except: pass
    return jsonify({"status": "success"})

@app.route("/api/control/override", methods=["POST"])
def manual_override():
    data = request.json
    category = data.get("category", "vintage-editorial")
    
    img_path = os.path.join(WORKSPACE, "static/vision_agent.jpg")
    if not os.path.exists(img_path): return jsonify({"error": "No image in buffer"})
    
    try:
        with open(img_path + ".status", "w") as sf: sf.write("MANUALLY ACCEPTED")
    except: pass
    
    import shutil, hashlib, json
    try:
        with open(img_path, 'rb') as f: img_bytes = f.read()
        img_hash = hashlib.md5(img_bytes).hexdigest()
        
        overrides_dir = os.path.join(WORKSPACE, "data/manual_overrides")
        os.makedirs(overrides_dir, exist_ok=True)
        shutil.copy(img_path, os.path.join(overrides_dir, f"{img_hash}.jpg"))
        
        EXTERNAL_VOLUME = "/Volumes/BT4TB/_CLIENTS/Ruby/All Ruby Projects/Interior Designer Inspiration"
        base_dir = EXTERNAL_VOLUME if os.path.exists(EXTERNAL_VOLUME) else os.path.join(WORKSPACE, "data")
        
        dir_mapping = {
            "wide": "Wides", "detail": "Macro_Textures", "lighting": "Lighting_Fixtures",
            "millwork": "Millwork_And_Joinery", "chair": "Designer_Chairs",
            "vintage-editorial": "Vintage_Editorial", "vintage-ad": "Vintage_Editorial/Ads"
        }
        
        folder = dir_mapping.get(category, category.capitalize())
        out_dir = os.path.join(base_dir, folder)
        os.makedirs(out_dir, exist_ok=True)
        
        final_path = os.path.join(out_dir, f"{img_hash}.jpg")
        if not os.path.exists(final_path):
            shutil.copy(img_path, final_path)
            
            meta_entry = {
                "filename": f"{img_hash}.jpg", "publication": "MANUAL_OVERRIDE",
                "source_url": "N/A", "cdn_url": "N/A", "assigned_category": category,
                "manual_override": True
            }
            with open(os.path.join(base_dir, "metadata_global.jsonl"), 'a') as mf: 
                mf.write(json.dumps(meta_entry) + "\n")
            with open(os.path.join(base_dir, "known_hashes_global.txt"), 'a') as hf:
                hf.write(f"{img_hash}\n")
    except Exception as e:
        return jsonify({"error": str(e)})
        
    return jsonify({"status": "success"})

@app.route("/api/system/ram")
def get_session_ram():
    import json
    EXTERNAL_VOLUME = "/Volumes/BT4TB/_CLIENTS/Ruby/All Ruby Projects/Interior Designer Inspiration"
    base_dir = EXTERNAL_VOLUME if os.path.exists(EXTERNAL_VOLUME) else os.path.join(WORKSPACE, "data")
    ram_file = os.path.join(base_dir, "session_ram.jsonl")
    
    lines = []
    if os.path.exists(ram_file):
        with open(ram_file, 'r') as f:
            all_lines = f.readlines()
            lines = [json.loads(l) for l in all_lines[-50:] if l.strip()]
            
    lines.reverse()
    return jsonify({"ram": lines})

@app.route("/api/system/ram_image/<filename>")
def serve_ram_image(filename):
    EXTERNAL_VOLUME = "/Volumes/BT4TB/_CLIENTS/Ruby/All Ruby Projects/Interior Designer Inspiration"
    base_dir = EXTERNAL_VOLUME if os.path.exists(EXTERNAL_VOLUME) else os.path.join(WORKSPACE, "data")
    return send_file(os.path.join(base_dir, "ram_cache", filename))

@app.route("/api/control/override_ram", methods=["POST"])
def override_ram():
    import shutil, json
    data = request.json
    hsh = data.get("hash")
    action = data.get("action")
    category = data.get("category", "vintage-editorial")
    
    EXTERNAL_VOLUME = "/Volumes/BT4TB/_CLIENTS/Ruby/All Ruby Projects/Interior Designer Inspiration"
    base_dir = EXTERNAL_VOLUME if os.path.exists(EXTERNAL_VOLUME) else os.path.join(WORKSPACE, "data")
    ram_dir = os.path.join(base_dir, "ram_cache")
    
    dir_mapping = {
        "wide": "Wides", "detail": "Macro_Textures", "lighting": "Lighting_Fixtures",
        "millwork": "Millwork_And_Joinery", "chair": "Designer_Chairs",
        "vintage-editorial": "Vintage_Editorial", "vintage-ad": "Vintage_Editorial/Ads"
    }
    
    try:
        if action == "rescue":
            src = os.path.join(ram_dir, f"{hsh}_rej.jpg")
            dst_folder = os.path.join(base_dir, dir_mapping.get(category, category.capitalize()))
            os.makedirs(dst_folder, exist_ok=True)
            dst = os.path.join(dst_folder, f"{hsh}.jpg")
            
            if os.path.exists(src):
                shutil.copy(src, dst)
                os.rename(src, os.path.join(ram_dir, f"{hsh}_acc.jpg"))
                
                with open(os.path.join(base_dir, "positive_overrides.txt"), 'a') as f: f.write(f"{hsh}\n")
                
                lines = []
                ram_file = os.path.join(base_dir, "session_ram.jsonl")
                with open(ram_file, 'r') as f: lines = f.readlines()
                with open(ram_file, 'w') as f:
                    for l in lines:
                        if not l.strip(): continue
                        obj = json.loads(l)
                        if obj.get("hash") == hsh:
                            obj["is_accepted"] = True
                            obj["filename"] = f"{hsh}_acc.jpg"
                            obj["assigned_category"] = category
                        f.write(json.dumps(obj) + "\n")
                        
        elif action == "delete":
            src = os.path.join(ram_dir, f"{hsh}_acc.jpg")
            if os.path.exists(src):
                os.rename(src, os.path.join(ram_dir, f"{hsh}_rej.jpg"))
                
            for v in dir_mapping.values():
                tgt = os.path.join(base_dir, v, f"{hsh}.jpg")
                if os.path.exists(tgt): os.remove(tgt)
                
            with open(os.path.join(base_dir, "negative_overrides.txt"), 'a') as f: f.write(f"{hsh}\n")
            
            lines = []
            ram_file = os.path.join(base_dir, "session_ram.jsonl")
            with open(ram_file, 'r') as f: lines = f.readlines()
            with open(ram_file, 'w') as f:
                for l in lines:
                    if not l.strip(): continue
                    obj = json.loads(l)
                    if obj.get("hash") == hsh:
                        obj["is_accepted"] = False
                        obj["filename"] = f"{hsh}_rej.jpg"
                    f.write(json.dumps(obj) + "\n")
                    
    except Exception as e:
        return jsonify({"error": str(e)})

    return jsonify({"status": "success"})

@app.route("/api/control/open_library", methods=["POST"])
def open_library():
    EXTERNAL_VOLUME = "/Volumes/BT4TB/_CLIENTS/Ruby/All Ruby Projects/Interior Designer Inspiration"
    if os.path.exists(EXTERNAL_VOLUME):
        target = EXTERNAL_VOLUME
    else:
        target = os.path.join(WORKSPACE, 'data')
        os.makedirs(target, exist_ok=True)
    os.system(f'open "{target}"')
    return jsonify({"status": "success"})
    
@app.route("/api/montage/index", methods=["POST"])
def run_geometry_tagging():
    EXTERNAL_VOLUME = "/Volumes/BT4TB/_CLIENTS/Ruby/All Ruby Projects/Interior Designer Inspiration"
    target_dir = EXTERNAL_VOLUME if os.path.exists(EXTERNAL_VOLUME) else os.path.join(WORKSPACE, "data")
    
    cmd = f"nohup venv/bin/python src/geometry_tagger.py --dir '{target_dir}' >> {WORKSPACE}/data/geometry.log 2>&1 &"
    os.system(cmd)
    return jsonify({"status": "indexing_started"})

@app.route("/api/montage/generate", methods=["POST"])
def generate_montage_endpoint():
    data = request.json
    concept = data.get("concept", "match-cut")
    anchor = data.get("anchor")
    perspective = data.get("perspective")
    limit = data.get("limit", 30)
    
    outfile_name = f"Montage_{concept}_{anchor}_{perspective}.fcpxml".replace(" ", "_").replace("/", "_")
    output_xml = os.path.join(os.path.expanduser("~"), "Desktop", outfile_name)
    
    cmd = f"venv/bin/python src/montage_generator.py --concept '{concept}' --anchor '{anchor}' --limit {limit} --out '{output_xml}'"
    if perspective:
        cmd += f" --perspective '{perspective}'"
    
    os.system(cmd)
    
    if os.path.exists(output_xml):
        return jsonify({"status": "success", "file": output_xml})
    else:
        return jsonify({"error": "Failed to generate sequence, not enough identically-framed images found."})
        
@app.route("/api/montage/status")
def montage_status():
    import subprocess
    cmd = f"ps aux | grep 'src/geometry_tagger.py' | grep -v grep | wc -l"
    try:
        count = int(subprocess.check_output(cmd, shell=True).strip())
        is_indexing = count > 0
    except:
        is_indexing = False
        
    db_path = "/Users/ben/.gemini/antigravity/playground/ghost-spirit/data/structural_manifest.jsonl"
    count = 0
    if os.path.exists(db_path):
        with open(db_path, "r") as f:
            count = sum(1 for line in f if line.strip())
            
    return jsonify({"indexing": is_indexing, "indexed_images": count})

@app.route("/api/clear", methods=["POST"])
def clear_logs():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w') as f: f.write("")
        
    EXTERNAL_VOLUME = "/Volumes/BT4TB/_CLIENTS/Ruby/All Ruby Projects/Interior Designer Inspiration"
    base_dir = EXTERNAL_VOLUME if os.path.exists(EXTERNAL_VOLUME) else os.path.join(WORKSPACE, "data")
    
    # Violently wipe Neural Memory DNA and visual RAM cache to prevent session bleed
    try:
        for fname in ["positive_overrides.txt", "negative_overrides.txt", "session_ram.jsonl"]:
            tgt = os.path.join(base_dir, fname)
            if os.path.exists(tgt):
                os.remove(tgt)
    except Exception as e:
        print(f"Memory wipe exception: {e}")
        
    return jsonify({"status": "success"})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050)
