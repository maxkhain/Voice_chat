"""
Audio encryption and decryption module.

Provides AES-256 encryption for audio and text data transmission.
Uses Fernet (symmetric encryption) which includes authentication and HMAC.
"""
from cryptography.fernet import Fernet
import os
import base64
import hashlib

# Global encryption key - generated or loaded
_ENCRYPTION_KEY = None
_CIPHER = None

# Default key derivation - uses a pre-shared secret
# In production, this could be derived from a handshake or password
DEFAULT_SECRET = b"local_voice_chat_default_secret"


def generate_key():
    """Generate a new random encryption key."""
    return Fernet.generate_key()


def derive_key_from_secret(secret: str) -> bytes:
    """
    Derive a consistent encryption key from a secret string.
    Useful for pre-shared keys between two users.
    
    Args:
        secret: String secret to derive key from
        
    Returns:
        bytes: Valid Fernet encryption key
    """
    # Hash the secret to get consistent 32 bytes, then base64 encode for Fernet
    hash_obj = hashlib.sha256(secret.encode())
    key = base64.urlsafe_b64encode(hash_obj.digest())
    return key


def initialize_encryption(key=None):
    """
    Initialize encryption with a specific key or generate a new one.
    
    Args:
        key: Optional bytes key. If None, derives from DEFAULT_SECRET
    """
    global _ENCRYPTION_KEY, _CIPHER
    
    if key is None:
        _ENCRYPTION_KEY = derive_key_from_secret(DEFAULT_SECRET.decode())
    else:
        _ENCRYPTION_KEY = key
    
    try:
        _CIPHER = Fernet(_ENCRYPTION_KEY)
        print("[OK] Encryption initialized")
    except Exception as e:
        print(f"[ERROR] Encryption initialization failed: {e}")
        return False
    
    return True


def get_encryption_key():
    """Get the current encryption key."""
    global _ENCRYPTION_KEY
    if _ENCRYPTION_KEY is None:
        initialize_encryption()
    return _ENCRYPTION_KEY


def encrypt_audio(audio_data: bytes) -> bytes:
    """
    Encrypt audio data.
    
    Args:
        audio_data: Raw audio bytes
        
    Returns:
        bytes: Encrypted audio data
    """
    global _CIPHER
    if _CIPHER is None:
        initialize_encryption()
    
    try:
        # Fernet returns bytes that include IV and authentication tag
        encrypted = _CIPHER.encrypt(audio_data)
        return encrypted
    except Exception as e:
        print(f"[ERROR] Encryption failed: {e}")
        return audio_data


def decrypt_audio(encrypted_data: bytes) -> bytes:
    """
    Decrypt audio data.
    
    Args:
        encrypted_data: Encrypted audio bytes
        
    Returns:
        bytes: Decrypted audio data, or empty bytes if decryption fails
    """
    global _CIPHER
    if _CIPHER is None:
        initialize_encryption()
    
    try:
        decrypted = _CIPHER.decrypt(encrypted_data)
        return decrypted
    except Exception as e:
        # Decryption failed - likely wrong key or corrupted data
        print(f"[ERROR] Decryption failed (may be wrong key): {e}")
        return b""


def encrypt_text(text: str) -> bytes:
    """
    Encrypt text message.
    
    Args:
        text: Text to encrypt
        
    Returns:
        bytes: Encrypted text
    """
    return encrypt_audio(text.encode('utf-8'))


def decrypt_text(encrypted_data: bytes) -> str:
    """
    Decrypt text message.
    
    Args:
        encrypted_data: Encrypted text bytes
        
    Returns:
        str: Decrypted text, or empty string if decryption fails
    """
    decrypted = decrypt_audio(encrypted_data)
    if not decrypted:
        return ""
    try:
        return decrypted.decode('utf-8')
    except Exception as e:
        print(f"[ERROR] Text decoding failed: {e}")
        return ""


def set_encryption_key_from_secret(secret: str):
    """
    Set encryption key derived from a shared secret (password/passphrase).
    Both users should call this with the same secret.
    
    Args:
        secret: Shared secret string
    """
    key = derive_key_from_secret(secret)
    initialize_encryption(key)
    print(f"[OK] Encryption key set from secret")


def get_key_summary():
    """Get a short summary of the current encryption key (for display/verification)."""
    global _ENCRYPTION_KEY
    if _ENCRYPTION_KEY is None:
        return "No key set"
    
    # Show first and last 8 chars of key for verification
    key_str = _ENCRYPTION_KEY.decode('utf-8')
    return f"{key_str[:8]}...{key_str[-8:]}"
