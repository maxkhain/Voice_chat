"""
Audio receiving functionality.
"""
import socket
import select
import time
from audio_config import CHUNK, PORT
import audio_sender

# Socket for receiving
sock = None

# Global state tracking
_RECV_QUEUE_DEPTH = 0

# Message type constants
MESSAGE_TYPE_AUDIO = b'\x00'
MESSAGE_TYPE_TEXT = b'\x01'

# Callback for receiving text messages
_text_message_callback = None


def set_text_message_callback(callback):
    """Set the callback function to be called when a text message is received."""
    global _text_message_callback
    _text_message_callback = callback


def initialize_receiver_socket():
    """Initialize and configure UDP socket for receiving audio."""
    global sock
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Ultra-minimal buffers to prevent accumulation
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 256)
    # NON-BLOCKING mode: recv returns immediately if no data
    sock.setblocking(False)
    sock.bind(('0.0.0.0', PORT))
    return sock


def get_receiver_socket():
    """Get the receiver socket, initializing if needed."""
    global sock
    if sock is None:
        initialize_receiver_socket()
    return sock


def receive_audio(output_stream):
    """
    Receive and play latest packet only; discard old ones if backlog exists.
    Also handles text messages.
    
    Args:
        output_stream: PyAudio output stream (speakers)
    """
    global _RECV_QUEUE_DEPTH
    
    sock = get_receiver_socket()
    
    while True:
        try:
            # Use select() to check if data is ready
            ready = select.select([sock], [], [], 0.01)
            if not ready[0]:
                # No data available
                time.sleep(0.001)
                continue
            
            # Receive the first packet
            data, _ = sock.recvfrom(CHUNK * 4)
            
            # Check message type
            if data and data[0:1] == MESSAGE_TYPE_TEXT:
                # Text message
                try:
                    message = data[1:].decode('utf-8')
                    if _text_message_callback:
                        _text_message_callback(message)
                except Exception as e:
                    print(f"Error decoding text message: {e}")
                continue
            
            # Audio data - drain old packets and keep latest
            drained = 0
            latest_data = data
            while drained < 5:
                try:
                    ready = select.select([sock], [], [], 0)
                    if not ready[0]:
                        break
                    latest_data, _ = sock.recvfrom(CHUNK * 4)
                    drained += 1
                except BlockingIOError:
                    break
            
            _RECV_QUEUE_DEPTH = drained
            # Update sender's UI with queue depth
            audio_sender.set_recv_queue_depth(drained)
            
            # Play ONLY the latest packet (discard old ones)
            try:
                output_stream.write(latest_data)
            except Exception:
                # Overflow; skip this frame only
                pass
                
        except BlockingIOError:
            time.sleep(0.001)
        except Exception as e:
            if "Errno 10054" not in str(e):
                break


def cleanup_receiver():
    """Clean up receiver socket."""
    global sock
    if sock:
        try:
            sock.close()
        except Exception:
            pass
        sock = None
