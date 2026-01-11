"""
User interface and user input handling.
"""
import pyaudio
from connection_cache import (
    get_last_connection,
    get_last_microphone,
    has_cached_connection,
    save_cache,
    display_cache_info,
)


def pick_microphone(p, auto_use_last=True):
    """
    List all available microphones and ask user to select one.
    
    Args:
        p: PyAudio instance
        auto_use_last: If True, automatically use last microphone (if available)
        
    Returns:
        Device index of selected microphone
        
    Raises:
        SystemExit: If no microphones are found
    """
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    input_devices = []

    for i in range(0, numdevices):
        if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            name = p.get_device_info_by_host_api_device_index(0, i).get('name')
            input_devices.append(i)

    if not input_devices:
        print("❌ No microphone found!")
        exit()
    
    # Try to use cached microphone
    if auto_use_last:
        last_mic_id = get_last_microphone()
        if last_mic_id is not None and last_mic_id in input_devices:
            last_mic_name = p.get_device_info_by_host_api_device_index(0, last_mic_id).get('name')
            print(f"\n📻 Using last microphone: {last_mic_name} (ID {last_mic_id})")
            response = input("Enter to continue, or 'n' to choose different microphone: ").strip().lower()
            if response != 'n':
                return last_mic_id
    
    # Show microphone selection menu
    print("\n--- Available Microphones ---")
    for i in input_devices:
        name = p.get_device_info_by_host_api_device_index(0, i).get('name')
        print(f"ID {i}: {name}")

    device_id = int(input("\nEnter the ID of the microphone you want to use: "))
    return device_id


def get_target_ip(auto_use_last=True):
    """
    Get target IP address with auto-connect option.
    
    Args:
        auto_use_last: If True, automatically use last connection (if available)
        
    Returns:
        IP address string
    """
    # Try to use cached connection
    if auto_use_last and has_cached_connection():
        last_ip = get_last_connection()
        print(f"\n📡 Last connection: {last_ip}")
        response = input("Enter to connect to same person, or 'n' to enter different IP: ").strip().lower()
        
        if response != 'n':
            return last_ip
    
    # Prompt for new IP
    target_ip = input("\nEnter the IP address of the OTHER person: ").strip()
    return target_ip


def display_welcome_message():
    """Display welcome message."""
    print("\n🎙️  Local Voice Chat - Low Latency Audio")
    print("=" * 50)


def display_goodbye_message():
    """Display goodbye message."""
    print("\n\n👋 Voice chat ended. Goodbye!")


def confirm_start():
    """Ask user to confirm start of voice chat."""
    response = input("\nReady to start voice chat? (yes/no): ").lower().strip()
    return response in ['yes', 'y']
