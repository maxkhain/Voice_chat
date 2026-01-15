# HexChat Project Structure

## Directory Organization

The project is organized into logical modules for better maintainability and clarity:

```
Voice_chat/
├── main.py                          # Main entry point
├── contacts.json                    # Saved contacts data file
├── .chat_history.json               # Chat history storage
├── .connection_cache.json           # Last connection settings
├── .scan_cache.json                 # Cached network scan results
├── .gitignore                       # Git ignore rules
├── create_shortcut.ps1              # PowerShell shortcut script
│
├── audio_modules/                   # Audio processing and I/O
│   ├── __init__.py
│   ├── audio_config.py             # Audio configuration constants
│   ├── audio_encryption.py         # Audio encryption/decryption
│   ├── audio_filter.py             # Audio filtering and DSP
│   ├── audio_io.py                 # PyAudio stream management
│   ├── audio_receiver.py           # Incoming audio and message handling
│   ├── audio_sender.py             # Outgoing audio transmission
│   ├── sound_effects.py            # Sound effects and notifications
│   └── sounds/                     # Sound files directory
│       ├── basic/                  # System notification sounds
│       │   ├── calling.wav
│       │   ├── cancelled.wav
│       │   ├── connected.wav
│       │   ├── disconnected.wav
│       │   ├── incoming.wav
│       │   ├── message.wav
│       │   └── rejected.wav
│       ├── fun/                    # Fun reaction sounds
│       │   ├── boing.wav
│       │   ├── drums.wav
│       │   └── squeaky.wav
│       └── reactions/              # Reaction sound effects
│           ├── cartoon-laugh.wav
│           ├── crowd-laugh.wav
│           ├── disappointed-trombone.wav
│           └── sad-trombone.wav
│
├── ui_modules/                      # User interface
│   ├── __init__.py
│   └── ui.py                       # CustomTkinter main GUI application
│
├── config/                          # Configuration and data management
│   ├── __init__.py
│   ├── chat_history.py             # Chat history storage and retrieval
│   └── contacts.py                 # Contact management system
│
├── utils/                           # Utility functions and tools
│   ├── __init__.py
│   ├── connection_cache.py         # Connection state caching
│   ├── scan_cache.py               # Network scan results caching
│   ├── network_scanner.py          # Network device discovery
│   ├── migrate_chat_history.py     # Chat history migration tools
│   ├── organize_sounds.py          # Sound file organization
│   ├── shortcut_generator.py       # Desktop shortcut creation
│   ├── build_shortcut_generator.bat # Build script for executable
│   └── run_hexchat.bat             # Windows launcher batch file
│
└── docs/                           # Documentation (14 files)
    ├── README.md                   # Documentation index
    ├── BUILD_SUMMARY.md            # Build and feature summary
    ├── CALL_TIMESTAMPS.md          # Call timestamping documentation
    ├── DATE_TIME_IMPLEMENTATION.md # Date/time feature details
    ├── EMOJI_SUPPORT.md            # Emoji functionality
    ├── PROJECT_STRUCTURE.md        # This file
    ├── QUICK_REFERENCE.md          # Quick reference guide
    ├── REORGANIZATION_SUMMARY.md   # Code reorganization details
    ├── SHORTCUT_GENERATOR_README.md # Shortcut generator guide
    ├── SOUND_BUTTONS_LAYOUT.md     # Sound button UI layout
    ├── SOUND_EFFECTS.md            # Sound effects system
    ├── TODO.md                     # Project tasks and roadmap
    ├── UI_IMPROVEMENTS.md          # UI enhancements
    └── VOLUME_CONTROL.md           # Volume control documentation
```

## Data Files (Root Level)

These files store persistent application data:
- **contacts.json**: Saved contacts with names and IPs
- **.chat_history.json**: All chat messages with timestamps
- **.connection_cache.json**: Last used IP, microphone, speaker
- **.scan_cache.json**: Cached network scan results
- **.chat_backups/**: Backup copies of chat history
- **.chat_history/**: Legacy chat history folder (if exists)

All modules use relative imports based on their location:

```python
# From audio_modules
from audio_modules.audio_config import RATE, CHUNK
from audio_modules.audio_sender import send_audio

# From ui_modules
from ui_modules.ui import HexChatApp

# From config
from config.chat_history import load_history
from config.contacts import get_all_contacts

# From utils
from utils.network_scanner import scan_network_async
from utils.connection_cache import get_last_connection
```

## Running the Application

### Option 1: Direct Python
```bash
python main.py
```

### Option 2: Batch Launcher
```bash
utils/run_hexchat.bat
```

### Option 3: Desktop Shortcut
Run the shortcut generator to create a desktop icon:
```bash
python utils/shortcut_generator.py
```

Or build it as an executable:
```bash
utils/build_shortcut_generator.bat
```

## Key Features by Module

### Audio Processing
- Real-time audio streaming via UDP
- Multiple audio filters (high-pass, low-pass, noise gate, etc.)
- Spectral subtraction for noise reduction
- Dynamic compression and limiting
- AES-256-GCM encryption for secure transmission

### UI/UX
- Tabbed chat interface for multiple contacts
- Drag-resizable sidebar
- Collapsible emoji and sound panels
- Real-time call status notifications
- Volume control for different sound types
- Network device scanning and discovery

### Data Management
- Persistent chat history with date separators
- Contact list with customizable names
- Connection state caching
- Network scan result caching

### Tools
- Desktop shortcut generator
- Sound file organization
- Network device discovery
- Chat history migration utilities

## Development Guidelines

When adding new features:

1. **Audio features** → `audio_modules/`
2. **UI components** → `ui_modules/ui.py`
3. **Data/Config** → `config/`
4. **Utility functions** → `utils/`
5. **Documentation** → `docs/`

Always update imports when using modules from different packages.

## Dependencies

- **customtkinter**: Modern GUI framework
- **pyaudio**: Audio I/O
- **numpy**: Audio processing
- **cryptography**: AES encryption
- **soundfile**: Audio file operations

See `requirements.txt` for complete list.
