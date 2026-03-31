import os
from google import genai
import fcntl

API_KEYS = [
    "AIzaSyD9lGFROb_EYFefJixKyQvqhFvKCQx-7VA",
    "AIzaSyA92wFPPGVn5toKEiKRYyxR0Wec-j_tNGg",
    "AIzaSyBrGtrn_wlrqHdGBrPdx5rFsVrdYPLp72k",
    "AIzaSyA99mrDF_lhiC2SuXJ2QNtieZEfXI9M14Q"
]

USAGE_FILE = "data/api_usage_tracker.txt"
FAILURE_FILE = "data/api_failure_tracker.txt"

def _increment_file(filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    count = 0
    try:
        with open(filepath, 'a+') as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.seek(0)
            data = f.read().strip()
            if data:
                count = int(data)
            count += 1
            f.seek(0)
            f.truncate()
            f.write(str(count))
            fcntl.flock(f, fcntl.LOCK_UN)
    except Exception as e:
        print(f"        [!] Rotator file error: {e}")
        count = 1
    return count

def _read_file(filepath):
    if not os.path.exists(filepath): return 0
    try:
        with open(filepath, 'r') as f:
            return int(f.read().strip())
    except:
        return 0

def get_current_client():
    # Increment the standard usage counter
    usage_count = _increment_file(USAGE_FILE)
    
    # Read how many times the API explicitly crashed from quota/billing
    failure_count = _read_file(FAILURE_FILE)
    
    # Key Index = Base rotation (every 1,450 calls to maximize standard Google free-tier quotas) + Any forced manual quota skips
    key_index = ((usage_count // 1450) + failure_count) % len(API_KEYS)
    active_key = API_KEYS[key_index]
    
    return genai.Client(api_key=active_key)

def rotate_to_next_key():
    """Called automatically when an API Exception regarding Quota or Billing is thrown."""
    _increment_file(FAILURE_FILE)
