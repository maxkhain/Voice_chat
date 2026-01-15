# HexChat Shortcut Generator

This tool creates a desktop shortcut for the HexChat P2P application.

## Quick Start

### Option 1: Run as Python Script
```bash
python shortcut_generator.py
```

### Option 2: Build as Standalone Executable
```bash
build_shortcut_generator.bat
```

This will create `HexChatShortcutGenerator.exe` in the `dist/` folder.

## Installation Requirements

### For Python Script
- Python 3.8+
- pywin32 (installed automatically if needed)

### For Executable Build
- Python 3.8+ (for building only)
- PyInstaller (installed automatically)
- pywin32 (installed automatically)

## How It Works

1. **Detects HexChat Location** - Searches for HexChat installation
2. **Creates Batch Launcher** - Generates `run_hexchat.bat` if not present
3. **Creates Desktop Shortcut** - Adds `HexChat.lnk` to Desktop

## Features

- Automatic HexChat path detection
- Batch launcher creation for proper Python environment setup
- Works with both PowerShell and Windows API methods
- Fallback options if primary method fails
- Detailed error messages

## Files Created

- `HexChat.lnk` - Desktop shortcut
- `run_hexchat.bat` - Batch launcher (if not present)

## Distribution

To distribute this tool:

1. Build the executable: `build_shortcut_generator.bat`
2. The executable in `dist/HexChatShortcutGenerator.exe` can be distributed standalone
3. Users can run it without needing Python installed

## Troubleshooting

### "Could not find HexChat installation"
- Ensure HexChat is installed in one of these locations:
  - `c:\Users\max\Documents\Local_voice\Voice_chat`
  - `%USERPROFILE%\Documents\Local_voice\Voice_chat`
  - Current directory / Voice_chat

### "Could not create shortcut"
- Try running as Administrator
- Check that Desktop folder is accessible
- Ensure Windows is fully updated

### Build Issues
- Run `pip install --upgrade PyInstaller pywin32`
- Delete `dist/` and `build/` folders before rebuilding
- Use `build_shortcut_generator.bat` for automated setup

## Advanced Options

### Custom Installation Path
Edit `shortcut_generator.py` and add your path to `possible_paths`:
```python
possible_paths = [
    Path("your/custom/path/Voice_chat"),
    ...
]
```

### Custom Icon
Modify the icon path in `create_windows_shortcut()`:
```python
shortcut.IconLocation = str(hexchat_path / "your_icon.ico")
```

## Support

For issues or questions, please check:
- HexChat installation is complete
- Python environment is properly configured
- Windows version is supported (Windows 7+)
