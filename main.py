"""
Main application entry point for Local Voice Chat.

Orchestrates initialization, audio setup, and starts send/receive threads.
"""
import threading
from audio_io import (
    get_audio_interface,
    open_input_stream,
    open_output_stream,
    close_stream,
    close_audio_interface
)
from audio_sender import send_audio, cleanup_sender
from audio_receiver import receive_audio, cleanup_receiver
from audio_filter import reset_noise_profile
from ui import (
    pick_microphone,
    get_target_ip,
    display_welcome_message,
    display_goodbye_message
)


def start_voice_chat():
    """
    Initialize audio streams, start receiver thread, and begin sending audio.
    """
    display_welcome_message()
    
    p = get_audio_interface()
    
    try:
        # 1. Select Microphone
        input_device_index = pick_microphone(p)

        # 2. Open input and output streams
        # CRITICAL: Separate input and output streams to avoid internal buffering delay
        input_stream = open_input_stream(p, input_device_index)
        output_stream = open_output_stream(p)

        # 3. Get target IP
        target_ip = get_target_ip()
        
        # 4. Reset noise profile for fresh session
        reset_noise_profile()

        # 5. Start receiver thread (listens for incoming audio)
        listener = threading.Thread(
            target=receive_audio,
            args=(output_stream,),
            daemon=True
        )
        listener.start()

        # 6. Send on main thread (higher priority, no context switching)
        send_audio(input_stream, output_stream, target_ip)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopping voice chat...")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        # Cleanup
        close_stream(input_stream)
        close_stream(output_stream)
        close_audio_interface(p)
        cleanup_sender()
        cleanup_receiver()
        display_goodbye_message()


if __name__ == "__main__":
    start_voice_chat()
