"""
Scan results cache for persisting network scan results.

Stores the last network scan results in a local JSON file.
Allows retrieving previous scan results even after app restart.
"""
import json
from pathlib import Path
from typing import List, Dict

# Cache file location
CACHE_DIR = Path(__file__).parent
CACHE_FILE = CACHE_DIR / ".scan_cache.json"

# Default cache structure
DEFAULT_CACHE = {
    "devices": [],
    "timestamp": None
}


def _load_cache() -> Dict:
    """
    Load scan cache from file.
    
    Returns:
        dict: Cache data with 'devices' list
        Returns default if file doesn't exist
    """
    try:
        if CACHE_FILE.exists():
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
    except Exception as e:
        print(f"[!] Could not load scan cache: {e}")
    
    return DEFAULT_CACHE.copy()


def _save_cache(data: Dict) -> None:
    """
    Save scan results to cache file.
    
    Args:
        data (dict): Cache data to save
    """
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[!] Could not save scan cache: {e}")


def save_scan_results(devices: List[str]) -> bool:
    """
    Save scan results (formatted device list).
    
    Args:
        devices (list): List of formatted device strings (e.g., "192.168.1.1 (Device Name)")
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        from datetime import datetime
        data = {
            "devices": devices,
            "timestamp": datetime.now().isoformat()
        }
        _save_cache(data)
        print(f"[OK] Saved {len(devices)} scan results to cache")
        return True
    except Exception as e:
        print(f"[!] Error saving scan results: {e}")
        return False


def load_scan_results() -> List[str]:
    """
    Load cached scan results.
    
    Returns:
        list: List of formatted device strings, or empty list if none cached
    """
    try:
        data = _load_cache()
        devices = data.get("devices", [])
        if devices:
            print(f"[OK] Loaded {len(devices)} devices from scan cache")
        return devices
    except Exception as e:
        print(f"[!] Error loading scan results: {e}")
        return []


def get_cache_timestamp() -> str:
    """
    Get the timestamp of the last scan.
    
    Returns:
        str: ISO format timestamp, or None if no cache
    """
    try:
        data = _load_cache()
        return data.get("timestamp")
    except Exception as e:
        print(f"[!] Error getting cache timestamp: {e}")
        return None


def clear_scan_cache() -> bool:
    """
    Clear the scan cache.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        _save_cache(DEFAULT_CACHE.copy())
        print(f"[OK] Cleared scan cache")
        return True
    except Exception as e:
        print(f"[!] Error clearing scan cache: {e}")
        return False
