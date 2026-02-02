"""
Build HexChat as a standalone executable using PyInstaller
"""
import PyInstaller.__main__
import os
import sys
from pathlib import Path

# Get the script directory
script_dir = Path(__file__).parent.absolute()
main_script = script_dir / "main.py"

# Icon file (you can add your own .ico file later)
icon_file = script_dir / "hexchat.ico"

# Build arguments for PyInstaller
build_args = [
    str(main_script),
    '--name=HexChat',
    '--onefile',  # Create a single executable
    '--windowed',  # No console window (GUI only)
    '--clean',
    f'--distpath={script_dir / "dist"}',
    f'--workpath={script_dir / "build"}',
    f'--specpath={script_dir}',
    
    # Add data files
    '--add-data=audio_modules;audio_modules',
    '--add-data=config;config',
    '--add-data=ui_modules;ui_modules',
    '--add-data=utils;utils',
    
    # Hidden imports that PyInstaller might miss
    '--hidden-import=flet',
    '--hidden-import=flet.matplotlib_chart',
    '--hidden-import=pygame',
    '--hidden-import=sounddevice',
    '--hidden-import=numpy',
    '--hidden-import=cryptography',
    '--hidden-import=cryptography.fernet',
    '--hidden-import=win32com.client',
    
    # Exclude unnecessary packages to reduce size
    '--exclude-module=matplotlib',
    '--exclude-module=PIL',
    '--exclude-module=tkinter',
]

# Add icon if it exists
if icon_file.exists():
    build_args.append(f'--icon={icon_file}')
else:
    print(f"Note: Icon file not found at {icon_file}")
    print("The executable will be created without a custom icon.")
    print("You can add a hexchat.ico file to the directory and rebuild.")

print("=" * 60)
print("Building HexChat Executable")
print("=" * 60)
print(f"Main script: {main_script}")
print(f"Output directory: {script_dir / 'dist'}")
print()

try:
    PyInstaller.__main__.run(build_args)
    print()
    print("=" * 60)
    print("Build completed successfully!")
    print("=" * 60)
    print(f"Executable location: {script_dir / 'dist' / 'HexChat.exe'}")
    print()
    print("Next steps:")
    print("1. Test the executable in the 'dist' folder")
    print("2. Run create_desktop_shortcut.ps1 to create a desktop shortcut")
    print("3. Optional: Add a hexchat.ico file and rebuild for a custom icon")
except Exception as e:
    print()
    print("=" * 60)
    print("Build failed!")
    print("=" * 60)
    print(f"Error: {e}")
    print()
    print("Make sure PyInstaller is installed:")
    print("  pip install pyinstaller")
    sys.exit(1)
