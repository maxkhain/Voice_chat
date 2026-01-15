"""
Chat history management for saving and loading message history.

Stores all messages from all contacts in a single consolidated JSON file.
Automatically creates backups after each message.
"""
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict


# Single consolidated chat history file
HISTORY_FILE = Path(__file__).parent / ".chat_history.json"

# Backup directory
BACKUP_DIR = Path(__file__).parent / ".chat_backups"
BACKUP_DIR.mkdir(exist_ok=True)

# Initialize history file if it doesn't exist
if not HISTORY_FILE.exists():
    with open(HISTORY_FILE, 'w') as f:
        json.dump({}, f, indent=2)


def load_all_chats() -> Dict:
    """
    Load the entire chat database.
    
    Returns:
        Dict: All chats organized by contact IP
    """
    try:
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"[ERROR] Could not load chat database: {e}")
    
    return {}


def save_all_chats(chats: Dict) -> bool:
    """
    Save the entire chat database.
    
    Args:
        chats: Dictionary of all chats by contact IP
        
    Returns:
        bool: True if successful
    """
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(chats, f, indent=2)
        return True
    except Exception as e:
        print(f"[ERROR] Could not save chat database: {e}")
        return False


def backup_history() -> bool:
    """
    Create a backup copy of entire chat history.
    
    Returns:
        bool: True if backup successful
    """
    try:
        if not HISTORY_FILE.exists():
            return True
        
        # Create backup with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = BACKUP_DIR / f"chat_history_backup_{timestamp}.json"
        
        # Copy file
        shutil.copy2(HISTORY_FILE, backup_file)
        
        # Keep only last 10 backups
        backups = sorted(BACKUP_DIR.glob("chat_history_backup_*.json"))
        if len(backups) > 10:
            for old_backup in backups[:-10]:
                old_backup.unlink()
        
        return True
    except Exception as e:
        print(f"[WARNING] Backup failed: {e}")
        return False


def add_message(contact_ip: str, sender: str, message: str) -> bool:
    """
    Add a message to chat history.
    
    Args:
        contact_ip: IP address of the contact
        sender: "You" or the contact's name/IP
        message: Message text
        
    Returns:
        bool: True if successful
    """
    try:
        # Load all chats
        chats = load_all_chats()
        
        # Initialize contact if not exists
        if contact_ip not in chats:
            chats[contact_ip] = []
        
        # Add new message
        msg_obj = {
            'timestamp': datetime.now().isoformat(),
            'sender': sender,
            'message': message
        }
        chats[contact_ip].append(msg_obj)
        
        # Save all chats
        if not save_all_chats(chats):
            return False
        
        return True
    except Exception as e:
        print(f"[ERROR] Could not save message: {e}")
        return False


def load_history(contact_ip: str) -> List[Dict]:
    """
    Load chat history for a contact from consolidated file.
    
    Args:
        contact_ip: IP address of the contact
        
    Returns:
        List[Dict]: List of message objects with timestamp, sender, message
    """
    try:
        chats = load_all_chats()
        return chats.get(contact_ip, [])
    except Exception as e:
        print(f"[ERROR] Could not load history: {e}")
        return []


def clear_history(contact_ip: str) -> bool:
    """
    Clear chat history for a specific contact.
    
    Args:
        contact_ip: IP address of the contact
        
    Returns:
        bool: True if successful
    """
    try:
        chats = load_all_chats()
        if contact_ip in chats:
            del chats[contact_ip]
            save_all_chats(chats)
            print(f"[OK] History cleared for {contact_ip}")
        return True
    except Exception as e:
        print(f"[ERROR] Could not clear history: {e}")
        return False


def format_timestamp(iso_timestamp: str) -> str:
    """
    Format ISO timestamp to readable format (time only).
    
    Args:
        iso_timestamp: ISO format timestamp string
        
    Returns:
        str: Formatted timestamp (e.g., "14:30:45")
    """
    try:
        dt = datetime.fromisoformat(iso_timestamp)
        # Return time only (HH:MM:SS)
        return dt.strftime("%H:%M:%S")
    except Exception:
        return iso_timestamp


def format_date_header(iso_timestamp: str) -> str:
    """
    Format ISO timestamp to date header (like WhatsApp/Discord).
    
    Args:
        iso_timestamp: ISO format timestamp string
        
    Returns:
        str: Formatted date header (e.g., "Today", "Yesterday", "January 12, 2026")
    """
    try:
        dt = datetime.fromisoformat(iso_timestamp)
        today = datetime.now().date()
        yesterday = today - __import__('datetime').timedelta(days=1)
        
        if dt.date() == today:
            return "Today"
        elif dt.date() == yesterday:
            return "Yesterday"
        else:
            return dt.strftime("%B %d, %Y")  # e.g., "January 12, 2026"
    except Exception:
        return "Unknown date"


def needs_date_separator(prev_timestamp: str, curr_timestamp: str) -> bool:
    """
    Check if a date separator should be inserted between two messages.
    
    Args:
        prev_timestamp: Previous message's ISO timestamp
        curr_timestamp: Current message's ISO timestamp
        
    Returns:
        bool: True if messages are on different dates
    """
    try:
        prev_dt = datetime.fromisoformat(prev_timestamp)
        curr_dt = datetime.fromisoformat(curr_timestamp)
        return prev_dt.date() != curr_dt.date()
    except Exception:
        return False


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
        chats = load_all_chats()
        return sorted(chats.keys())
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
    Get formatted history for display with date separators (like WhatsApp/Discord).
    
    Args:
        contact_ip: IP address of the contact
        max_messages: Maximum messages to return (None = all)
        
    Returns:
        str: Formatted history text with date separators
    """
    messages = load_history(contact_ip)
    
    if max_messages:
        messages = messages[-max_messages:]
    
    lines = []
    prev_date = None
    
    for msg in messages:
        timestamp = msg.get('timestamp', '')
        sender = msg.get('sender', 'Unknown')
        text = msg.get('message', '')
        
        # Check if we need a date separator
        curr_date = format_date_header(timestamp)
        if curr_date != prev_date:
            # Add date separator
            lines.append(f"\n--- {curr_date} ---")
            prev_date = curr_date
        
        # Format the message with time only
        time_str = format_timestamp(timestamp)
        lines.append(f"[{time_str}] {sender}: {text}")
    
    return "\n".join(lines) if lines else "(No messages)"


def get_formatted_message(sender: str, message: str, timestamp: str = None) -> str:
    """
    Format a single message with timestamp for display.
    
    Args:
        sender: Message sender name
        message: Message text
        timestamp: ISO timestamp (uses current time if not provided)
        
    Returns:
        str: Formatted message string
    """
    if timestamp is None:
        timestamp = datetime.now().isoformat()
    
    formatted_time = format_timestamp(timestamp)
    return f"[{formatted_time}] {sender}: {message}"
