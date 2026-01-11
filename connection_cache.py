"""
Connection cache management for auto-connect functionality.

Stores the last used connection details in a local JSON file.
Allows resuming the last connection automatically on startup.
"""
import json
import os
from pathlib import Path

# Cache file location - stored in the workspace directory
CACHE_DIR = Path(__file__).parent
CACHE_FILE = CACHE_DIR / ".connection_cache.json"

# Default cache structure
DEFAULT_CACHE = {
    "last_connection": None,
    "microphone_device_id": None,
    "timestamp": None,
}


def get_cache_path():
    """Return the path to the cache file."""
    return CACHE_FILE


def load_cache():
    """
    Load connection cache from file.
    
    Returns:
        dict: Cache data with 'last_connection' and 'microphone_device_id'
        Returns default cache if file doesn't exist
    """
    try:
        if CACHE_FILE.exists():
            with open(CACHE_FILE, 'r') as f:
                cache = json.load(f)
                return cache
    except Exception as e:
        print(f"⚠️  Could not load cache: {e}")
    
    return DEFAULT_CACHE.copy()


def save_cache(target_ip, microphone_device_id=None):
    """
    Save connection details to cache file.
    
    Args:
        target_ip (str): IP address of the other person
        microphone_device_id (int, optional): Device ID of selected microphone
    """
    try:
        cache = {
            "last_connection": target_ip,
            "microphone_device_id": microphone_device_id,
            "timestamp": str(Path(__file__).stat().st_mtime),
        }
        
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f, indent=2)
        
        print(f"✓ Connection saved to cache")
    except Exception as e:
        print(f"⚠️  Could not save cache: {e}")


def get_last_connection():
    """
    Get the last saved connection IP address.
    
    Returns:
        str: Last connection IP, or None if not cached
    """
    cache = load_cache()
    return cache.get('last_connection')


def get_last_microphone():
    """
    Get the last used microphone device ID.
    
    Returns:
        int: Last microphone device ID, or None if not cached
    """
    cache = load_cache()
    return cache.get('microphone_device_id')


def clear_cache():
    """Clear the cache file."""
    try:
        if CACHE_FILE.exists():
            CACHE_FILE.unlink()
            print("✓ Cache cleared")
    except Exception as e:
        print(f"⚠️  Could not clear cache: {e}")


def has_cached_connection():
    """Check if there's a cached connection."""
    last_ip = get_last_connection()
    return last_ip is not None and last_ip.strip() != ""


def display_cache_info():
    """Display current cache information."""
    cache = load_cache()
    last_ip = cache.get('last_connection')
    last_mic = cache.get('microphone_device_id')
    
    print("\n=== Connection Cache ===")
    if last_ip:
        print(f"  Last IP: {last_ip}")
    else:
        print(f"  Last IP: (none)")
    
    if last_mic is not None:
        print(f"  Last Microphone ID: {last_mic}")
    else:
        print(f"  Last Microphone ID: (none)")
    print()
