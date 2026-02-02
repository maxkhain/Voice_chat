"""
Application settings persistence for HexChat.
Stores volume levels and device selections locally.
"""
import json
from pathlib import Path

SETTINGS_FILE = Path(__file__).parent / "app_settings.json"

DEFAULT_SETTINGS = {
    "volumes": {
        "call": 70,
        "message_incoming": 60,
        "message_outgoing": 50,
        "incoming_voice": 100,
        "sound_effects": 50
    },
    "devices": {
        "microphone_index": None,
        "speaker_index": None
    }
}


def load_settings():
    """Load settings from file."""
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"[WARNING] Could not load settings: {e}")
    
    return DEFAULT_SETTINGS.copy()


def save_settings(settings):
    """Save settings to file."""
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
        print("[OK] Settings saved")
        return True
    except Exception as e:
        print(f"[ERROR] Could not save settings: {e}")
        return False


def get_volume_settings():
    """Get volume settings."""
    settings = load_settings()
    return settings.get("volumes", DEFAULT_SETTINGS["volumes"])


def save_volume_settings(volumes):
    """Save volume settings."""
    settings = load_settings()
    settings["volumes"] = volumes
    return save_settings(settings)


def get_device_settings():
    """Get device settings."""
    settings = load_settings()
    return settings.get("devices", DEFAULT_SETTINGS["devices"])


def save_device_settings(devices):
    """Save device settings."""
    settings = load_settings()
    settings["devices"] = devices
    return save_settings(settings)
