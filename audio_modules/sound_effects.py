"""
Sound effects manager for various events in the voice chat application.

Handles playing sounds for:
- Outgoing calls
- Incoming calls
- Call connected
- Call rejected
- Disconnected
- New message received
- Call cancelled
- Custom sounds during calls
"""
import os
import sys
import threading
from pathlib import Path


# Volume settings (0.0 to 1.0)
_volume_call = 0.7  # Call sounds (outgoing/incoming)
_volume_message_incoming = 0.6  # Incoming message sounds
_volume_message_outgoing = 0.5  # Outgoing message sounds
_volume_incoming_voice = 1.0  # Incoming voice volume
_volume_sound_effects = 0.5  # Fun/reaction sound effects (50% default)

# Callback for sending custom sounds to remote peer
_send_custom_sound_callback = None


def set_send_custom_sound_callback(callback):
    """
    Set callback for sending custom sounds to the remote peer.
    
    Args:
        callback: Function that takes (sound_name, category) as parameters
    """
    global _send_custom_sound_callback
    _send_custom_sound_callback = callback


def set_call_volume(volume: float):
    """Set volume for call sounds (calling, incoming). Range: 0.0 to 1.0"""
    global _volume_call
    _volume_call = max(0.0, min(1.0, volume))


def set_message_incoming_volume(volume: float):
    """Set volume for incoming message sounds. Range: 0.0 to 1.0"""
    global _volume_message_incoming
    _volume_message_incoming = max(0.0, min(1.0, volume))


def set_message_outgoing_volume(volume: float):
    """Set volume for outgoing message sounds. Range: 0.0 to 1.0"""
    global _volume_message_outgoing
    _volume_message_outgoing = max(0.0, min(1.0, volume))


def get_call_volume() -> float:
    """Get current call sounds volume."""
    return _volume_call


def get_message_incoming_volume() -> float:
    """Get current incoming message sounds volume."""
    return _volume_message_incoming


def get_message_outgoing_volume() -> float:
    """Get current outgoing message sounds volume."""
    return _volume_message_outgoing


def set_incoming_voice_volume(volume: float):
    """Set volume for incoming voice audio. Range: 0.0 to 1.0"""
    global _volume_incoming_voice
    _volume_incoming_voice = max(0.0, min(1.0, volume))


def get_incoming_voice_volume() -> float:
    """Get current incoming voice volume."""
    return _volume_incoming_voice


def set_sound_effects_volume(volume: float):
    """Set volume for fun/reaction sound effects. Range: 0.0 to 1.0"""
    global _volume_sound_effects
    _volume_sound_effects = max(0.0, min(1.0, volume))
    print(f"[DEBUG] Sound effects volume set to: {_volume_sound_effects}")


def get_sound_effects_volume() -> float:
    """Get current fun/reaction sound effects volume."""
    return _volume_sound_effects


# Sound effect file paths
SOUNDS_DIR = Path(__file__).parent / "sounds"
SOUNDS_DIR.mkdir(exist_ok=True)

# Basic system sounds paths
SOUND_CALLING = SOUNDS_DIR / "basic" / "calling.wav"
SOUND_INCOMING = SOUNDS_DIR / "basic" / "incoming.wav"
SOUND_CONNECTED = SOUNDS_DIR / "basic" / "connected.wav"
SOUND_REJECTED = SOUNDS_DIR / "basic" / "rejected.wav"
SOUND_DISCONNECTED = SOUNDS_DIR / "basic" / "disconnected.wav"
SOUND_MESSAGE = SOUNDS_DIR / "basic" / "message.wav"
SOUND_CANCELLED = SOUNDS_DIR / "basic" / "cancelled.wav"


def _generate_tone(frequency: float, duration_ms: int) -> bytes:
    """
    Generate a simple sine wave tone.
    
    Args:
        frequency: Frequency in Hz
        duration_ms: Duration in milliseconds
        
    Returns:
        bytes: WAV file bytes
    """
    import wave
    import struct
    import math
    import io
    
    sample_rate = 44100
    num_samples = int(sample_rate * duration_ms / 1000)
    
    # Generate samples
    samples = []
    for i in range(num_samples):
        sample = int(32767 * 0.3 * math.sin(2 * math.pi * frequency * i / sample_rate))
        samples.append(sample)
    
    # Create WAV in memory
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        for sample in samples:
            wav_file.writeframes(struct.pack('<h', sample))
    
    return wav_buffer.getvalue()


def _create_default_sounds():
    """Create default sound files if they don't exist."""
    try:
        # Create basic directory if needed
        basic_dir = SOUNDS_DIR / "basic"
        basic_dir.mkdir(exist_ok=True)
        
        # Calling tone - repeating 880 Hz
        if not SOUND_CALLING.exists():
            wav_data = _generate_tone(880, 200)
            with open(SOUND_CALLING, 'wb') as f:
                f.write(wav_data)
            print(f"[OK] Created {SOUND_CALLING}")
        
        # Incoming call - repeating pattern (660 Hz)
        if not SOUND_INCOMING.exists():
            wav_data = _generate_tone(660, 300)
            with open(SOUND_INCOMING, 'wb') as f:
                f.write(wav_data)
            print(f"[OK] Created {SOUND_INCOMING}")
        
        # Connected - ascending tones (523 Hz, 659 Hz, 783 Hz)
        if not SOUND_CONNECTED.exists():
            import io
            import wave
            import struct
            import math
            
            sample_rate = 44100
            wav_buffer = io.BytesIO()
            
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                
                for freq in [523, 659, 783]:  # Do, Mi, Sol
                    num_samples = int(sample_rate * 100 / 1000)
                    for i in range(num_samples):
                        sample = int(32767 * 0.3 * math.sin(2 * math.pi * freq * i / sample_rate))
                        wav_file.writeframes(struct.pack('<h', sample))
            
            with open(SOUND_CONNECTED, 'wb') as f:
                f.write(wav_buffer.getvalue())
            print(f"[OK] Created {SOUND_CONNECTED}")
        
        # Rejected - descending tones
        if not SOUND_REJECTED.exists():
            import io
            import wave
            import struct
            import math
            
            sample_rate = 44100
            wav_buffer = io.BytesIO()
            
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                
                for freq in [659, 523, 330]:  # Mi, Do, Mi (lower)
                    num_samples = int(sample_rate * 100 / 1000)
                    for i in range(num_samples):
                        sample = int(32767 * 0.3 * math.sin(2 * math.pi * freq * i / sample_rate))
                        wav_file.writeframes(struct.pack('<h', sample))
            
            with open(SOUND_REJECTED, 'wb') as f:
                f.write(wav_buffer.getvalue())
            print(f"[OK] Created {SOUND_REJECTED}")
        
        # Disconnected - single tone
        if not SOUND_DISCONNECTED.exists():
            wav_data = _generate_tone(440, 200)
            with open(SOUND_DISCONNECTED, 'wb') as f:
                f.write(wav_data)
            print(f"[OK] Created {SOUND_DISCONNECTED}")
        
        # Message received - chime (two tones)
        if not SOUND_MESSAGE.exists():
            import io
            import wave
            import struct
            import math
            
            sample_rate = 44100
            wav_buffer = io.BytesIO()
            
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                
                # Two ascending tones
                for freq in [523, 783]:  # Do, Sol
                    num_samples = int(sample_rate * 150 / 1000)
                    for i in range(num_samples):
                        sample = int(32767 * 0.3 * math.sin(2 * math.pi * freq * i / sample_rate))
                        wav_file.writeframes(struct.pack('<h', sample))
            
            with open(SOUND_MESSAGE, 'wb') as f:
                f.write(wav_buffer.getvalue())
            print(f"[OK] Created {SOUND_MESSAGE}")
        
        # Cancelled - single short tone
        if not SOUND_CANCELLED.exists():
            wav_data = _generate_tone(440, 150)
            with open(SOUND_CANCELLED, 'wb') as f:
                f.write(wav_data)
            print(f"[OK] Created {SOUND_CANCELLED}")
        
    except Exception as e:
        print(f"[WARNING] Could not create sound files: {e}")


def play_sound(sound_file: Path, loop: bool = False, volume: float = 1.0):
    """
    Play a sound file asynchronously.
    
    Args:
        sound_file: Path to WAV file
        loop: Whether to loop the sound
        volume: Volume level (0.0 to 1.0)
    """
    if not sound_file.exists():
        print(f"[WARNING] Sound file not found: {sound_file}")
        return
    
    def _play_in_thread():
        try:
            if sys.platform == "win32":
                # For looping sounds on Windows, use winsound (can be stopped with stop_all_sounds)
                if loop:
                    _play_sound_windows(sound_file, loop)
                else:
                    # For non-looping sounds, use pygame for volume control
                    _play_sound_cross_platform(sound_file, loop, volume)
            else:
                _play_sound_cross_platform(sound_file, loop, volume)
        except Exception as e:
            print(f"[ERROR] Could not play sound: {e}")
    
    thread = threading.Thread(target=_play_in_thread, daemon=True)
    thread.start()


def _play_sound_windows(sound_file: Path, loop: bool = False):
    """Play sound using Windows winsound module."""
    try:
        import winsound
        
        flags = winsound.SND_FILENAME
        if loop:
            flags |= winsound.SND_LOOP
        else:
            flags |= winsound.SND_ASYNC
        
        winsound.PlaySound(str(sound_file), flags)
    except Exception as e:
        print(f"[WARNING] Windows sound playback failed: {e}")
        try:
            _play_sound_cross_platform(sound_file, loop)
        except Exception as e2:
            print(f"[ERROR] Cross-platform fallback also failed: {e2}")


def _play_sound_cross_platform(sound_file: Path, loop: bool = False, volume: float = 1.0):
    """Play sound using pygame mixer (cross-platform fallback)."""
    try:
        import pygame
        # Initialize mixer only once
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        
        sound = pygame.mixer.Sound(str(sound_file))
        sound.set_volume(volume)  # Set volume (0.0 to 1.0)
        print(f"[DEBUG] Pygame playing {sound_file.name} at volume {volume}")
        
        if loop:
            sound.play(-1)  # Loop indefinitely
        else:
            sound.play()
    except ImportError:
        print("[WARNING] pygame not installed, skipping sound playback")
    except Exception as e:
        print(f"[WARNING] Pygame playback failed: {e}")
        import traceback
        traceback.print_exc()


def stop_all_sounds():
    """Stop all currently playing sounds."""
    try:
        if sys.platform == "win32":
            import winsound
            winsound.PlaySound(None, 0)  # Stop winsound on Windows
        # Also stop pygame sounds (used for volume-controlled playback)
        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.stop()
        except Exception:
            pass
    except Exception as e:
        print(f"[WARNING] Could not stop sounds: {e}")


# Sound event functions
def sound_calling():
    """Play sound when initiating a call."""
    play_sound(SOUND_CALLING, loop=True, volume=_volume_call)


def sound_incoming():
    """Play sound when receiving an incoming call."""
    play_sound(SOUND_INCOMING, loop=True, volume=_volume_call)


def sound_connected():
    """Play sound when call is connected."""
    stop_all_sounds()  # Stop calling/incoming sounds
    play_sound(SOUND_CONNECTED, volume=_volume_call)


def sound_rejected():
    """Play sound when call is rejected."""
    stop_all_sounds()
    play_sound(SOUND_REJECTED, volume=_volume_call)


def sound_disconnected():
    """Play sound when call is disconnected."""
    stop_all_sounds()
    play_sound(SOUND_DISCONNECTED, volume=_volume_call)


def sound_message():
    """Play sound when message is received (incoming)."""
    play_sound(SOUND_MESSAGE, volume=_volume_message_incoming)


def sound_message_sent():
    """Play sound when message is sent (outgoing)."""
    play_sound(SOUND_MESSAGE, volume=_volume_message_outgoing)


def sound_cancelled():
    """Play sound when call is cancelled."""
    stop_all_sounds()
    play_sound(SOUND_CANCELLED, volume=_volume_call)


def get_available_sounds(category: str = None):
    """
    Get all available sound files organized by category.
    
    Args:
        category: Optional category filter ('fun', 'reactions', 'basic')
        
    Returns:
        dict: Category -> [list of sound files]
    """
    available = {}
    
    for category_dir in SOUNDS_DIR.iterdir():
        if not category_dir.is_dir():
            continue
        
        cat_name = category_dir.name
        if category and cat_name != category:
            continue
        
        sounds = []
        for sound_file in sorted(category_dir.glob("*.wav")):
            sounds.append({
                'path': sound_file,
                'name': sound_file.stem,  # Clean name without extension
                'display': sound_file.stem.replace('-', ' ').title()
            })
        
        if sounds:
            available[cat_name] = sounds
    
    return available


def get_fun_sounds():
    """Get all fun/reaction sounds that can be sent during calls."""
    available = get_available_sounds()
    fun_sounds = []
    
    # Include both fun and reaction categories
    for category in ['fun', 'reactions']:
        if category in available:
            fun_sounds.extend(available[category])
    
    return fun_sounds


def play_custom_sound(sound_name: str, category: str = 'fun'):
    """
    Play a custom fun/reaction sound during a call.
    
    This is called ONLY for LOCAL playback when receiving a sound from remote peer.
    For sending sounds, use send_text_message with __SOUND__ prefix instead.
    
    Args:
        sound_name: Name of the sound file (without extension)
        category: Category ('fun' or 'reactions')
    """
    sound_file = SOUNDS_DIR / category / f"{sound_name}.wav"
    if sound_file.exists():
        print(f"[DEBUG] Playing {sound_name} at volume {_volume_sound_effects}")
        play_sound(sound_file, volume=_volume_sound_effects)
    else:
        print(f"[WARNING] Sound not found: {sound_name}")


# Initialize sounds on import
_create_default_sounds()
