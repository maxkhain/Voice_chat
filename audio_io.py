"""
Audio input and output stream management.
"""
import pyaudio
from audio_config import CHANNELS, RATE, FORMAT, CHUNK


def get_audio_interface():
    """Initialize and return PyAudio interface."""
    return pyaudio.PyAudio()


def open_input_stream(p, input_device_index):
    """
    Open an audio input stream (microphone).
    
    Args:
        p: PyAudio instance
        input_device_index: Device index for input
        
    Returns:
        Input stream object
    """
    return p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        input_device_index=input_device_index,
        frames_per_buffer=CHUNK
    )


def open_output_stream(p):
    """
    Open an audio output stream (speakers).
    
    Args:
        p: PyAudio instance
        
    Returns:
        Output stream object
    """
    return p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        output=True,
        frames_per_buffer=CHUNK
    )


def close_stream(stream):
    """Close an audio stream."""
    if stream:
        try:
            stream.stop_stream()
            stream.close()
        except Exception:
            pass


def close_audio_interface(p):
    """Terminate PyAudio interface."""
    if p:
        try:
            p.terminate()
        except Exception:
            pass
