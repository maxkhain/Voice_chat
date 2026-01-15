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
"""
import os
import sys
import threading
from pathlib import Path


# Volume settings (0.0 to 1.0)
_volume_call = 0.7  # Call sounds (outgoing/incoming)
_volume_message_incoming = 0.6  # Incoming message sounds
_volume_message_outgoing = 0.5  # Outgoing message sounds


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


# Sound effect file paths
SOUNDS_DIR = Path(__file__).parent / "sounds"

# Create sounds directory if it doesn't exist
SOUNDS_DIR.mkdir(exist_ok=True)

# Sound file names
SOUND_CALLING = SOUNDS_DIR / "calling.wav"
SOUND_INCOMING = SOUNDS_DIR / "incoming.wav"
SOUND_CONNECTED = SOUNDS_DIR / "connected.wav"
SOUND_REJECTED = SOUNDS_DIR / "rejected.wav"
SOUND_DISCONNECTED = SOUNDS_DIR / "disconnected.wav"
SOUND_MESSAGE = SOUNDS_DIR / "message.wav"
SOUND_CANCELLED = SOUNDS_DIR / "cancelled.wav"


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
                _play_sound_windows(sound_file, loop)
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
        import pygame  # noqa - optional dependency for fallback
        pygame.mixer.init()
        sound = pygame.mixer.Sound(str(sound_file))
        sound.set_volume(volume)  # Set volume (0.0 to 1.0)
        
        if loop:
            sound.play(-1)  # Loop indefinitely
        else:
            sound.play()
    except ImportError:
        print("[WARNING] pygame not installed, skipping sound playback")
    except Exception as e:
        print(f"[WARNING] Pygame fallback failed: {e}")


def stop_all_sounds():
    """Stop all currently playing sounds."""
    try:
        if sys.platform == "win32":
            import winsound
            winsound.PlaySound(None, 0)  # Stop all sounds on Windows
        else:
            try:
                import pygame
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


# Initialize sounds on import
_create_default_sounds()
