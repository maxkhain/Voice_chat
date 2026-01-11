"""
User interface and user input handling.
"""
import pyaudio


def pick_microphone(p):
    """
    List all available microphones and ask user to select one.
    
    Args:
        p: PyAudio instance
        
    Returns:
        Device index of selected microphone
        
    Raises:
        SystemExit: If no microphones are found
    """
    print("\n--- Available Microphones ---")
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    input_devices = []

    for i in range(0, numdevices):
        if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            name = p.get_device_info_by_host_api_device_index(0, i).get('name')
            input_devices.append(i)
            print(f"ID {i}: {name}")

    if not input_devices:
        print("❌ No microphone found!")
        exit()
        
    device_id = int(input("\nEnter the ID of the microphone you want to use: "))
    return device_id


def get_target_ip():
    """
    Prompt user for target IP address.
    
    Returns:
        IP address string
    """
    target_ip = input("\nEnter the IP address of the OTHER person: ")
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
