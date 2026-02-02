# Building HexChat as an Executable

This guide will help you create a standalone executable for HexChat that you can run from your desktop.

## Prerequisites

1. **Python Environment**: Make sure Python is installed and your virtual environment is activated
2. **PyInstaller**: Install PyInstaller if not already installed
   ```bash
   pip install pyinstaller
   ```

## Step 1: Build the Executable

Run the build script:
```bash
python build_executable.py
```

This will:
- Create a standalone `HexChat.exe` in the `dist` folder
- Bundle all dependencies (no Python required to run)
- Package all necessary modules and resources

**Build time**: ~1-2 minutes (first build may take longer)

## Step 2: Create Desktop Shortcut

Run the PowerShell script to create a desktop icon:
```powershell
powershell -ExecutionPolicy Bypass -File create_desktop_shortcut.ps1
```

This creates a "HexChat" icon on your desktop that launches the executable.

## Optional: Add Custom Icon

1. Create or download a `.ico` file for your app
2. Save it as `hexchat.ico` in the project root
3. Rebuild the executable: `python build_executable.py`
4. Recreate the shortcut: `powershell -ExecutionPolicy Bypass -File create_desktop_shortcut.ps1`

## File Locations

After building:
- **Executable**: `dist/HexChat.exe`
- **Build files**: `build/` (can be deleted)
- **Spec file**: `HexChat.spec` (PyInstaller configuration)

## Distribution

To share the app with others:
1. Copy the `HexChat.exe` from the `dist` folder
2. Users can run it directly - no Python installation needed
3. The app will create config files in the directory where it runs

## Troubleshooting

### "PyInstaller not found"
```bash
pip install pyinstaller
```

### "Executable won't run"
- Make sure all dependencies are installed in your environment
- Check Windows Defender/Antivirus (may flag new executables)
- Try running from command line to see error messages

### "Missing modules"
- Add missing imports to the `--hidden-import` list in `build_executable.py`
- Rebuild after adding imports

### "Sounds not working"
- Ensure `audio_modules/sounds/` folder exists with sound files
- Check that `--add-data` includes the sounds directory

## Quick Reference

**Build**: `python build_executable.py`
**Shortcut**: `powershell -ExecutionPolicy Bypass -File create_desktop_shortcut.ps1`
**Run**: Double-click desktop icon or run `dist/HexChat.exe`
**Clean**: Delete `build/` and `dist/` folders, then rebuild

## Advanced Options

Edit `build_executable.py` to customize:
- `--onefile` vs `--onedir`: Single file or folder with DLLs
- `--windowed`: Remove to show console for debugging
- `--name`: Change executable name
- Add more `--add-data` for additional resources
- Add more `--hidden-import` for missing packages
