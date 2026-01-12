"""
Chat history management for saving and loading message history.

Stores messages per contact with timestamps in JSON format.
Automatically creates backups after each message.
"""
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict


# Chat history directory
HISTORY_DIR = Path(__file__).parent / ".chat_history"
HISTORY_DIR.mkdir(exist_ok=True)

# Backup directory
BACKUP_DIR = Path(__file__).parent / ".chat_backups"
BACKUP_DIR.mkdir(exist_ok=True)


def get_history_file(contact_ip: str) -> Path:
    """
    Get the history file path for a contact.
    
    Args:
        contact_ip: IP address of the contact
        
    Returns:
        Path: Path to the history file
    """
    # Sanitize IP for filename
    safe_name = contact_ip.replace('.', '_')
    return HISTORY_DIR / f"chat_{safe_name}.json"


def backup_history(contact_ip: str) -> bool:
    """
    Create a backup copy of chat history after each message.
    
    Args:
        contact_ip: IP address of the contact
        
    Returns:
        bool: True if backup successful
    """
    try:
        history_file = get_history_file(contact_ip)
        if not history_file.exists():
            return True
        
        # Create backup with timestamp
        safe_name = contact_ip.replace('.', '_')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = BACKUP_DIR / f"chat_{safe_name}_backup_{timestamp}.json"
        
        # Copy file
        shutil.copy2(history_file, backup_file)
        
        # Keep only last 10 backups per contact
        backups = sorted(BACKUP_DIR.glob(f"chat_{safe_name}_backup_*.json"))
        if len(backups) > 10:
            for old_backup in backups[:-10]:
                old_backup.unlink()
        
        return True
    except Exception as e:
        print(f"[WARNING] Backup failed: {e}")
        return False


def add_message(contact_ip: str, sender: str, message: str) -> bool:
    """
    Add a message to chat history and create backup.
    
    Args:
        contact_ip: IP address of the contact
        sender: "You" or the contact's name/IP
        message: Message text
        
    Returns:
        bool: True if successful
    """
    try:
        history_file = get_history_file(contact_ip)
        
        # Load existing messages
        messages = []
        if history_file.exists():
            with open(history_file, 'r') as f:
                messages = json.load(f)
        
        # Add new message
        msg_obj = {
            'timestamp': datetime.now().isoformat(),
            'sender': sender,
            'message': message
        }
        messages.append(msg_obj)
        
        # Save messages
        with open(history_file, 'w') as f:
            json.dump(messages, f, indent=2)
        
        # Create backup after each message
        backup_history(contact_ip)
        
        return True
    except Exception as e:
        print(f"[ERROR] Could not save message: {e}")
        return False


def load_history(contact_ip: str) -> List[Dict]:
    """
    Load chat history for a contact.
    
    Args:
        contact_ip: IP address of the contact
        
    Returns:
        List[Dict]: List of message objects with timestamp, sender, message
    """
    try:
        history_file = get_history_file(contact_ip)
        
        if not history_file.exists():
            return []
        
        with open(history_file, 'r') as f:
            messages = json.load(f)
        
        return messages
    except Exception as e:
        print(f"[ERROR] Could not load history: {e}")
        return []


def clear_history(contact_ip: str) -> bool:
    """
    Clear chat history for a contact.
    
    Args:
        contact_ip: IP address of the contact
        
    Returns:
        bool: True if successful
    """
    try:
        history_file = get_history_file(contact_ip)
        if history_file.exists():
            history_file.unlink()
            print(f"[OK] History cleared for {contact_ip}")
        return True
    except Exception as e:
        print(f"[ERROR] Could not clear history: {e}")
        return False


def format_timestamp(iso_timestamp: str) -> str:
    """
    Format ISO timestamp to readable format.
    
    Args:
        iso_timestamp: ISO format timestamp string
        
    Returns:
        str: Formatted timestamp (e.g., "14:30:45" or "Jan 12 14:30")
    """
    try:
        dt = datetime.fromisoformat(iso_timestamp)
        # Return time only if today, date + time if older
        today = datetime.now().date()
        if dt.date() == today:
            return dt.strftime("%H:%M:%S")
        else:
            return dt.strftime("%b %d %H:%M")
    except Exception:
        return iso_timestamp


def export_history(contact_ip: str, format: str = "text") -> str:
    """
    Export chat history in specified format.
    
    Args:
        contact_ip: IP address of the contact
        format: "text" or "json"
        
    Returns:
        str: Exported content
    """
    messages = load_history(contact_ip)
    
    if format == "json":
        return json.dumps(messages, indent=2)
    else:  # text format
        lines = [f"Chat History with {contact_ip}"]
        lines.append("=" * 50)
        for msg in messages:
            timestamp = format_timestamp(msg.get('timestamp', ''))
            sender = msg.get('sender', 'Unknown')
            text = msg.get('message', '')
            lines.append(f"[{timestamp}] {sender}: {text}")
        return "\n".join(lines)


def get_contact_list() -> List[str]:
    """
    Get list of all contacts with chat history.
    
    Returns:
        List[str]: List of contact IPs
    """
    try:
        contacts = []
        if HISTORY_DIR.exists():
            for file in HISTORY_DIR.glob("chat_*.json"):
                # Extract IP from filename
                name = file.stem.replace("chat_", "")
                ip = name.replace("_", ".")
                contacts.append(ip)
        return sorted(contacts)
    except Exception:
        return []


def get_history_size(contact_ip: str) -> int:
    """
    Get number of messages in history.
    
    Args:
        contact_ip: IP address of the contact
        
    Returns:
        int: Number of messages
    """
    messages = load_history(contact_ip)
    return len(messages)


def display_history(contact_ip: str, max_messages: int = None) -> str:
    """
    Get formatted history for display.
    
    Args:
        contact_ip: IP address of the contact
        max_messages: Maximum messages to return (None = all)
        
    Returns:
        str: Formatted history text
    """
    messages = load_history(contact_ip)
    
    if max_messages:
        messages = messages[-max_messages:]
    
    lines = []
    for msg in messages:
        timestamp = format_timestamp(msg.get('timestamp', ''))
        sender = msg.get('sender', 'Unknown')
        text = msg.get('message', '')
        lines.append(f"[{timestamp}] {sender}: {text}")
    
    return "\n".join(lines) if lines else "(No messages)"
