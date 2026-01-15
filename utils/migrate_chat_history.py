#!/usr/bin/env python3
"""
Migration script to consolidate old per-contact chat files into single unified file.
Run this once to migrate existing chat history from .chat_history/*.json to .chat_history.json
"""

import json
import shutil
from pathlib import Path
from chat_history import HISTORY_FILE, HISTORY_DIR

def migrate_old_format():
    """Migrate from per-contact files to consolidated file."""
    
    old_history_dir = Path(__file__).parent / ".chat_history"
    
    if not old_history_dir.exists():
        print("[OK] No old chat history directory found. Nothing to migrate.")
        return True
    
    # Check if there are old chat files
    old_files = list(old_history_dir.glob("chat_*.json"))
    
    if not old_files:
        print("[OK] No old chat files found. Nothing to migrate.")
        return True
    
    print(f"[INFO] Found {len(old_files)} old chat files to migrate...")
    
    # Load consolidated file (or create empty)
    consolidated = {}
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, 'r') as f:
                consolidated = json.load(f)
        except Exception as e:
            print(f"[WARNING] Could not load existing consolidated file: {e}")
    
    # Migrate each old file
    migrated_count = 0
    for old_file in old_files:
        try:
            # Extract IP from filename (chat_192_168_1_50.json -> 192.168.1.50)
            name = old_file.stem.replace("chat_", "")
            contact_ip = name.replace("_", ".")
            
            # Load old messages
            with open(old_file, 'r') as f:
                messages = json.load(f)
            
            # Add to consolidated (don't overwrite existing)
            if contact_ip not in consolidated:
                consolidated[contact_ip] = messages
                migrated_count += 1
                print(f"  [OK] Migrated {contact_ip} ({len(messages)} messages)")
            else:
                print(f"  [SKIP] {contact_ip} already exists in consolidated file")
        
        except Exception as e:
            print(f"  [ERROR] Failed to migrate {old_file.name}: {e}")
    
    # Save consolidated file
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(consolidated, f, indent=2)
        print(f"\n[OK] Successfully migrated {migrated_count} contact(s)")
        
        # Backup old directory
        backup_dir = old_history_dir.parent / ".chat_history_old"
        if old_history_dir.exists():
            shutil.move(str(old_history_dir), str(backup_dir))
            print(f"[OK] Backed up old directory to {backup_dir.name}/")
        
        return True
    
    except Exception as e:
        print(f"[ERROR] Failed to save consolidated file: {e}")
        return False

if __name__ == "__main__":
    migrate_old_format()
