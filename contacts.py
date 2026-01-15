"""
Contact management for saving device IPs with custom names.

Stores and retrieves contacts from a local JSON file.
Allows searching for devices and saving them with names.
"""
import json
import os
from pathlib import Path
from typing import List, Dict, Optional

# Contacts file location
CONTACTS_DIR = Path(__file__).parent
CONTACTS_FILE = CONTACTS_DIR / "contacts.json"

# Default contacts structure
DEFAULT_CONTACTS = {
    "contacts": []
}


def _load_contacts() -> Dict:
    """
    Load contacts from file.
    
    Returns:
        dict: Contacts data with list of contact entries
        Returns default if file doesn't exist
    """
    try:
        if CONTACTS_FILE.exists():
            with open(CONTACTS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
    except Exception as e:
        print(f"[!] Could not load contacts: {e}")
    
    return DEFAULT_CONTACTS.copy()


def _save_contacts(data: Dict) -> None:
    """
    Save contacts to file.
    
    Args:
        data (dict): Contacts data to save
    """
    try:
        with open(CONTACTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[!] Could not save contacts: {e}")


def add_contact(ip: str, name: Optional[str] = None) -> bool:
    """
    Add a new contact or update existing one.
    
    Args:
        ip (str): IP address of the contact
        name (str, optional): Custom name for the contact. Defaults to "piggy" if not provided
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not ip or not _is_valid_ip(ip):
        print(f"[!] Invalid IP address: {ip}")
        return False
    
    # Use "piggy" as default name if none provided
    contact_name = name if name and name.strip() else "piggy"
    contact_name = contact_name.strip()
    
    try:
        data = _load_contacts()
        
        # Check if contact already exists
        for contact in data["contacts"]:
            if contact["ip"] == ip:
                # Update existing contact
                contact["name"] = contact_name
                _save_contacts(data)
                print(f"[OK] Updated contact: {contact_name} ({ip})")
                return True
        
        # Add new contact
        new_contact = {
            "ip": ip,
            "name": contact_name
        }
        data["contacts"].append(new_contact)
        _save_contacts(data)
        print(f"[OK] Added contact: {contact_name} ({ip})")
        return True
    
    except Exception as e:
        print(f"[!] Error adding contact: {e}")
        return False


def remove_contact(ip: str) -> bool:
    """
    Remove a contact by IP address.
    
    Args:
        ip (str): IP address of the contact to remove
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        data = _load_contacts()
        original_length = len(data["contacts"])
        
        data["contacts"] = [c for c in data["contacts"] if c["ip"] != ip]
        
        if len(data["contacts"]) < original_length:
            _save_contacts(data)
            print(f"[OK] Removed contact: {ip}")
            return True
        else:
            print(f"[!] Contact not found: {ip}")
            return False
    
    except Exception as e:
        print(f"[!] Error removing contact: {e}")
        return False


def get_contact_name(ip: str) -> Optional[str]:
    """
    Get the name of a contact by IP address.
    
    Args:
        ip (str): IP address to look up
    
    Returns:
        str: Contact name, or None if not found
    """
    try:
        data = _load_contacts()
        for contact in data["contacts"]:
            if contact["ip"] == ip:
                return contact["name"]
    except Exception as e:
        print(f"[!] Error getting contact name: {e}")
    
    return None


def get_contact_ip(name: str) -> Optional[str]:
    """
    Get the IP address of a contact by name.
    
    Args:
        name (str): Contact name to look up
    
    Returns:
        str: IP address, or None if not found
    """
    try:
        data = _load_contacts()
        for contact in data["contacts"]:
            if contact["name"].lower() == name.lower():
                return contact["ip"]
    except Exception as e:
        print(f"[!] Error getting contact IP: {e}")
    
    return None


def get_all_contacts() -> List[Dict]:
    """
    Get all saved contacts.
    
    Returns:
        list: List of contact dictionaries with 'ip' and 'name' keys
    """
    try:
        data = _load_contacts()
        return data.get("contacts", [])
    except Exception as e:
        print(f"[!] Error getting contacts: {e}")
        return []


def search_contacts(query: str) -> List[Dict]:
    """
    Search contacts by name or IP address.
    
    Args:
        query (str): Search term (partial match on name or IP)
    
    Returns:
        list: List of matching contact dictionaries
    """
    query_lower = query.lower()
    matches = []
    
    try:
        contacts = get_all_contacts()
        for contact in contacts:
            if (query_lower in contact["name"].lower() or 
                query_lower in contact["ip"]):
                matches.append(contact)
    except Exception as e:
        print(f"[!] Error searching contacts: {e}")
    
    return matches


def _is_valid_ip(ip: str) -> bool:
    """
    Validate IP address format.
    
    Args:
        ip (str): IP address to validate
    
    Returns:
        bool: True if valid IPv4 address, False otherwise
    """
    parts = ip.split('.')
    if len(parts) != 4:
        return False
    
    try:
        for part in parts:
            num = int(part)
            if num < 0 or num > 255:
                return False
        return True
    except ValueError:
        return False


def contact_exists(ip: str) -> bool:
    """
    Check if a contact exists by IP address.
    
    Args:
        ip (str): IP address to check
    
    Returns:
        bool: True if contact exists, False otherwise
    """
    return get_contact_name(ip) is not None


def get_contacts_display_list() -> List[str]:
    """
    Get formatted list of contacts for display (Name - IP).
    
    Returns:
        list: List of formatted contact strings
    """
    try:
        contacts = get_all_contacts()
        return [f"{c['name']} - {c['ip']}" for c in contacts]
    except Exception as e:
        print(f"[!] Error getting contacts display list: {e}")
        return []


def extract_ip_from_contact_display(display_str: str) -> Optional[str]:
    """
    Extract IP from formatted contact display string.
    
    Args:
        display_str (str): Formatted string like "Name - IP"
    
    Returns:
        str: IP address, or None if invalid format
    """
    try:
        if " - " in display_str:
            return display_str.split(" - ")[-1].strip()
    except Exception as e:
        print(f"[!] Error extracting IP from display: {e}")
    
    return None
