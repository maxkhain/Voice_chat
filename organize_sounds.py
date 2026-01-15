"""
Organize sound files into categories and clean up names.
"""
import os
import shutil
from pathlib import Path

SOUNDS_DIR = Path(__file__).parent / "sounds"

# Category mappings
SOUND_CATEGORIES = {
    # Basic/System sounds (for call events)
    "basic": [
        "calling.wav",
        "incoming.wav",
        "connected.wav",
        "rejected.wav",
        "disconnected.wav",
        "cancelled.wav",
        "message.wav",
    ],
    # Fun/Sound effects that can be sent in calls
    "fun": [
        "mixkit-boing-hit-sound-2894.wav",
        "mixkit-funny-squeaky-toy-hits-2813.wav",
        "mixkit-joke-drums-578.wav",
    ],
    # Emotional/Reaction sounds
    "reactions": [
        "mixkit-cartoon-laugh-voice-2882.wav",
        "mixkit-crowd-laugh-424.wav",
        "mixkit-sad-game-over-trombone-471.wav",
        "mixkit-trombone-disappoint-744.wav",
    ],
}

# Clean name mappings
CLEAN_NAMES = {
    "calling.wav": "calling.wav",
    "incoming.wav": "incoming.wav",
    "connected.wav": "connected.wav",
    "rejected.wav": "rejected.wav",
    "disconnected.wav": "disconnected.wav",
    "cancelled.wav": "cancelled.wav",
    "message.wav": "message.wav",
    "mixkit-boing-hit-sound-2894.wav": "boing.wav",
    "mixkit-funny-squeaky-toy-hits-2813.wav": "squeaky.wav",
    "mixkit-joke-drums-578.wav": "drums.wav",
    "mixkit-cartoon-laugh-voice-2882.wav": "cartoon-laugh.wav",
    "mixkit-crowd-laugh-424.wav": "crowd-laugh.wav",
    "mixkit-sad-game-over-trombone-471.wav": "sad-trombone.wav",
    "mixkit-trombone-disappoint-744.wav": "disappointed-trombone.wav",
}


def organize_sounds():
    """Organize sound files into category folders with clean names."""
    
    if not SOUNDS_DIR.exists():
        print(f"Sounds directory not found: {SOUNDS_DIR}")
        return
    
    # Create category folders
    for category in SOUND_CATEGORIES.keys():
        category_dir = SOUNDS_DIR / category
        category_dir.mkdir(exist_ok=True)
    
    # Move and rename files
    for category, files in SOUND_CATEGORIES.items():
        category_dir = SOUNDS_DIR / category
        
        for filename in files:
            old_path = SOUNDS_DIR / filename
            if old_path.exists():
                # Get clean name
                clean_name = CLEAN_NAMES.get(filename, filename)
                new_path = category_dir / clean_name
                
                # Move file
                shutil.move(str(old_path), str(new_path))
                print(f"✓ Moved {filename} → {category}/{clean_name}")
            else:
                print(f"⚠ Not found: {filename}")
    
    print("\n✅ Sound organization complete!")
    print(f"   Basic: {len(SOUND_CATEGORIES['basic'])} files")
    print(f"   Fun: {len(SOUND_CATEGORIES['fun'])} files")
    print(f"   Reactions: {len(SOUND_CATEGORIES['reactions'])} files")


if __name__ == "__main__":
    organize_sounds()
