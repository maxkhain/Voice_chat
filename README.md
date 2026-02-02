# HexChat - P2P Voice and Text Chat

A peer-to-peer voice and text chat application built with Python and Flet. Features end-to-end encryption, real-time voice communication, and a modern cross-platform GUI.

## Features

- 🎤 **Real-time Voice Chat**: High-quality P2P voice communication
- 💬 **Text Messaging**: Send instant messages with chat history
- 🔐 **End-to-End Encryption**: All communications are encrypted
- 📞 **Call Management**: Incoming call notifications, mutual call detection
- 🎵 **Sound Effects**: Audio notifications for calls, messages, and events
- 📱 **Contact Management**: Save and organize your contacts
- 🔊 **Volume Controls**: Separate volume settings for different audio types
- 🎨 **Modern UI**: Clean, responsive interface built with Flet
- 🖥️ **Cross-Platform**: Windows support (macOS/Linux compatible)

## Quick Start

### Running from Source

1. **Install Python 3.9+**

2. **Clone or download this repository**

3. **Install dependencies**:
   ```bash
   pip install -r requirements-build.txt
   ```

4. **Run the application**:
   ```bash
   python main.py
   ```

### Building as Executable

1. **Install build requirements**:
   ```bash
   pip install pyinstaller
   ```

2. **Build the executable**:
   ```bash
   python build_executable.py
   ```
   Or simply run:
   ```bash
   build_and_deploy.bat
   ```

3. **Create desktop shortcut**:
   ```powershell
   powershell -ExecutionPolicy Bypass -File create_desktop_shortcut.ps1
   ```

The executable will be in the `dist/` folder.

## Usage

### Making a Call

1. Add contacts using the contacts dropdown
2. Select a contact
3. Click "Connect Voice/Chat"
4. Accept/reject incoming calls with the popup dialog

### Sending Messages

1. Select a contact from "Chat with" dropdown
2. Type your message
3. Press Enter or click Send

### Audio Controls

- **Mute**: Toggle microphone on/off
- **Deafen**: Toggle speaker on/off
- **Volume**: Adjust individual volume sliders in settings

## Project Structure

```
Voice_chat/
├── main.py                      # Application entry point
├── audio_modules/               # Audio processing
│   ├── audio_io.py             # Audio device management
│   ├── audio_sender.py         # Audio transmission
│   ├── audio_receiver.py       # Audio reception
│   ├── audio_filter.py         # Noise reduction
│   ├── audio_encryption.py     # Audio encryption
│   ├── audio_config.py         # Audio configuration
│   ├── sound_effects.py        # Sound notifications
│   └── sounds/                 # Sound effect files
├── ui_modules/                  # User interface
│   ├── ui_layout_flet.py       # UI layout components
│   └── ui_backend_flet.py      # Backend logic integration
├── config/                      # Configuration
│   ├── contacts.py             # Contact management
│   ├── chat_history.py         # Chat history storage
│   ├── app_settings.py         # App settings
│   └── app_settings.json       # Settings file
├── utils/                       # Utility functions
│   ├── network_scanner.py      # Network device discovery
│   ├── connection_cache.py     # Connection caching
│   └── organize_sounds.py      # Sound file organizer
├── docs/                        # Documentation
├── build_executable.py          # Executable builder
├── build_and_deploy.bat         # Build automation
└── create_desktop_shortcut.ps1  # Shortcut creator
```

## Configuration

### Settings File
Settings are stored in `config/app_settings.json`:
- Volume levels for different audio types
- Window size and position
- User preferences

### Contacts
Contacts are stored in `config/contacts.json`

### Chat History
Chat history is stored in `.chat_history.json`

## Network Requirements

- **Ports**: Uses UDP for voice (default: dynamic)
- **Local Network**: Works on same WiFi/LAN
- **Direct IP**: Connect via direct IP address

## Troubleshooting

### No Audio
- Check microphone/speaker permissions
- Select correct audio devices
- Verify volume settings

### Connection Failed
- Ensure both devices are on same network
- Check firewall settings
- Verify IP address is correct

### Executable Won't Run
- Check Windows Defender/Antivirus
- Run from command line to see errors
- Rebuild with `python build_executable.py`

## Development

### Requirements
- Python 3.9 or higher
- Dependencies listed in `requirements-build.txt`

### Key Dependencies
- **Flet**: UI framework
- **PyAudio/sounddevice**: Audio I/O
- **Cryptography**: Encryption
- **Pygame**: Sound effects
- **NumPy**: Audio processing

### Contributing
See individual module documentation in the `docs/` folder.

## Documentation

- [Build Instructions](BUILD_INSTRUCTIONS.md)
- [Project Structure](docs/PROJECT_STRUCTURE.md)
- [Sound Effects](docs/SOUND_EFFECTS.md)
- [Call Flow](docs/CALLING_LOGIC_FLOW.md)
- [UI Improvements](docs/UI_IMPROVEMENTS.md)

## License

This project is for educational and personal use.

## Support

For issues or questions, check the documentation in the `docs/` folder.

---

**Built with ❤️ using Python and Flet**
