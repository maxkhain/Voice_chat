# HexChat - Quick Reference Guide

## What Was Just Done

✓ **Fixed Sound Duplication Bug**
- Sound buttons were calling the wrong function
- Changed from `play_custom_sound()` to `send_custom_sound()` 
- Now sounds are only sent once per click

✓ **Moved Sound Controls to Settings**
- Removed volume sliders from sidebar clutter
- Added them to the Settings window where they belong
- Settings now has a scrollable interface

✓ **Reorganized Project Structure**
- Created logical folders:
  - `audio_modules/` - All audio processing
  - `ui_modules/` - GUI components  
  - `config/` - Data management
  - `utils/` - Helper tools
  - `docs/` - All documentation

✓ **Created Standalone Shortcut Generator**
- `shortcut_generator.py` - Python script for creating desktop shortcuts
- `build_shortcut_generator.bat` - Build it as a Windows executable
- Can be distributed to other machines

## File Organization

### Before
```
Voice_chat/
├── *.py (15+ loose files)
├── *.md (10+ loose docs)
├── sounds/
└── __pycache__/
```

### After
```
Voice_chat/
├── main.py (entry point)
├── audio_modules/      (7 audio files)
├── ui_modules/         (GUI)
├── config/            (data management)
├── utils/             (tools & helpers)
├── docs/              (all documentation)
├── sounds/            (sound files)
└── config/ (folders)
```

## Key Imports (Updated)

### In main.py
```python
from ui_modules.ui import HexChatApp  # Changed from 'from ui'
```

### In ui.py
```python
from audio_modules.audio_io import get_audio_interface
from audio_modules.audio_sender import send_audio
from config.chat_history import load_history
from utils.network_scanner import scan_network_async
```

## Running the Application

### Option 1: Python (Recommended for Development)
```bash
cd c:\Users\max\Documents\Local_voice\Voice_chat
python main.py
```

### Option 2: Batch Launcher
```bash
utils/run_hexchat.bat
```

### Option 3: Desktop Shortcut
First time setup:
```bash
python utils/shortcut_generator.py
```

Then click the HexChat icon on your desktop!

## Volume Control Location

**Old:** Sidebar (cluttered)
**New:** Settings Window → Scroll down → 🔊 Sound Effects

Controls:
- **Call Volume** - Ring tone volume
- **📥 Received Message Volume** - Incoming message sounds
- **📤 Sent Message Volume** - Outgoing message sounds

## Sound Button Fix

**Problem:** Clicking once sent sound multiple times
**Root Cause:** Button callback was calling `play_custom_sound()` directly
**Solution:** Changed to `send_custom_sound()` which properly manages the single send

Now:
- Click once = Sound sent once ✓
- Sound plays on both sides ✓
- Message shows in chat ✓

## Important Files

| File | Purpose |
|------|---------|
| `main.py` | Start here |
| `ui_modules/ui.py` | GUI application |
| `audio_modules/audio_sender.py` | Send audio |
| `audio_modules/audio_receiver.py` | Receive audio |
| `utils/shortcut_generator.py` | Create shortcuts |
| `docs/PROJECT_STRUCTURE.md` | Detailed structure |

## Next Steps

1. **Test the application:**
   ```bash
   python main.py
   ```

2. **Create desktop shortcut (optional):**
   ```bash
   python utils/shortcut_generator.py
   ```

3. **Build shortcut generator as .exe (optional):**
   ```bash
   utils/build_shortcut_generator.bat
   ```

## Module Purposes at a Glance

- **audio_modules/** - Audio I/O, encryption, filters, effects
- **ui_modules/** - CustomTkinter GUI application
- **config/** - Chat history, contacts database
- **utils/** - Network scanner, cache, tools
- **docs/** - All documentation and guides
- **sounds/** - Audio files organized by category

## Common Tasks

### Add a new feature to audio
→ Create file in `audio_modules/`
→ Update imports in `ui_modules/ui.py`

### Add a new UI component
→ Modify `ui_modules/ui.py`
→ Update relevant imports

### Store new configuration
→ Add to `config/`
→ Create getter/setter functions

### Add a utility function
→ Create file in `utils/`
→ Export in `utils/__init__.py`

## Documentation

See `docs/` folder for detailed guides:
- `PROJECT_STRUCTURE.md` - Complete project structure
- `SHORTCUT_GENERATOR_README.md` - Building the shortcut tool
- `SOUND_EFFECTS.md` - Sound system details
- `UI_IMPROVEMENTS.md` - UI features
- And more...

## Support

All code is well-organized and documented. Check the relevant module for implementation details.
