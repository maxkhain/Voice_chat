"""
Audio sending functionality.
"""
import socket
import time
import audioop
from audio_config import CHUNK, PORT
from audio_filter import apply_noise_cancellation

# Socket for sending
sock = None

# Global state tracking
_LAST_VISUAL = 0.0
_SEND_QUEUE_DEPTH = 0
_RECV_QUEUE_DEPTH = 0

# For visual feedback
VISUAL_THROTTLE = 0.1

# Message type constants
MESSAGE_TYPE_AUDIO = b'\x00'
MESSAGE_TYPE_TEXT = b'\x01'


def initialize_sender_socket():
    """Initialize and configure UDP socket for sending audio."""
    global sock
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 256)
    sock.setblocking(False)
    return sock


def get_sender_socket():
    """Get the sender socket, initializing if needed."""
    global sock
    if sock is None:
        initialize_sender_socket()
    return sock


def set_recv_queue_depth(depth):
    """Update received packet queue depth for UI display."""
    global _RECV_QUEUE_DEPTH
    _RECV_QUEUE_DEPTH = depth


def send_text_message(message, target_ip):
    """
    Send a text message to the target IP.
    
    Args:
        message: Text message to send
        target_ip: Target IP address
    """
    try:
        sock = get_sender_socket()
        # Prepend message type byte and encode text
        packet = MESSAGE_TYPE_TEXT + message.encode('utf-8')
        sock.sendto(packet, (target_ip, PORT))
    except Exception as e:
        print(f"Error sending text message: {e}")


def send_audio(input_stream, output_stream, target_ip):
    """
    Read microphone and send audio immediately for smooth, natural audio.
    
    Args:
        input_stream: PyAudio input stream (microphone)
        output_stream: PyAudio output stream (for monitoring if needed)
        target_ip: Target IP address to send audio to
    """
    global _LAST_VISUAL, _SEND_QUEUE_DEPTH
    
    print(f"\n🎤 Sending audio to {target_ip}...")
    print(f"(Clean, unprocessed audio for smooth quality)")
    
    sock = get_sender_socket()
    
    while True:
        try:
            # Read one frame from mic
            data = input_stream.read(CHUNK, exception_on_overflow=False)
            
            # Apply noise cancellation (disabled by default for smooth audio)
            data = apply_noise_cancellation(data)
            
            # Prepend message type (audio) and send immediately
            try:
                packet = MESSAGE_TYPE_AUDIO + data
                sock.sendto(packet, (target_ip, PORT))
                _SEND_QUEUE_DEPTH = 0
            except BlockingIOError:
                _SEND_QUEUE_DEPTH = 1
            
            # Throttled visual update
            now = time.time()
            if now - _LAST_VISUAL >= VISUAL_THROTTLE:
                _LAST_VISUAL = now
                try:
                    rms = audioop.rms(data, 2)  
                    bars = "█" * int((rms / 300))
                    status = f"Vol: {bars[:50].ljust(50)} [Rx:{_RECV_QUEUE_DEPTH}]"
                    print(f"\r{status[:75]}", end="", flush=False)
                except Exception:
                    pass
        except Exception:
            break


def cleanup_sender():
    """Clean up sender socket."""
    global sock
    if sock:
        try:
            sock.close()
        except Exception:
            pass
        sock = None
