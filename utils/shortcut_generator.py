#!/usr/bin/env python3
"""
HexChat Shortcut Generator
Creates a desktop shortcut for the HexChat P2P application
Can be packaged as a standalone executable using PyInstaller
"""

import os
import sys
import json
from pathlib import Path


def get_hexchat_path():
    """Determine the HexChat installation path."""
    # Try to find HexChat in common locations
    possible_paths = [
        Path("c:/Users/max/Documents/Local_voice/Voice_chat"),
        Path.home() / "Documents" / "Local_voice" / "Voice_chat",
        Path.cwd() / "Voice_chat",
    ]
    
    for path in possible_paths:
        if path.exists() and (path / "main.py").exists():
            return path
    
    return None


def create_batch_launcher(hexchat_path):
    """Create a batch file launcher if it doesn't exist."""
    batch_file = hexchat_path / "run_hexchat.bat"
    
    if batch_file.exists():
        return batch_file
    
    batch_content = """@echo off
REM HexChat P2P Voice/Chat Application
REM This batch file runs the HexChat application

cd /d "{}"

REM Run the Python application
python main.py

REM Pause to show any error messages
if errorlevel 1 pause
""".format(hexchat_path)
    
    try:
        batch_file.write_text(batch_content)
        return batch_file
    except Exception as e:
        print(f"Error creating batch file: {e}")
        return None


def create_windows_shortcut():
    """Create a Windows shortcut to the HexChat application."""
    try:
        import win32com.client
    except ImportError:
        print("Installing required package: pywin32...")
        os.system("pip install pywin32")
        try:
            import win32com.client
        except ImportError:
            print("ERROR: Could not import win32com.client")
            print("Please install pywin32: pip install pywin32")
            return False
    
    hexchat_path = get_hexchat_path()
    if not hexchat_path:
        print("ERROR: Could not find HexChat installation")
        print("Please ensure HexChat is installed in:")
        print("  c:\\Users\\max\\Documents\\Local_voice\\Voice_chat")
        return False
    
    # Create batch launcher
    batch_file = create_batch_launcher(hexchat_path)
    if not batch_file:
        print("ERROR: Could not create batch launcher")
        return False
    
    # Create desktop shortcut
    desktop_path = Path.home() / "Desktop"
    shortcut_path = desktop_path / "HexChat.lnk"
    
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(str(shortcut_path))
        shortcut.TargetPath = str(batch_file)
        shortcut.WorkingDirectory = str(hexchat_path)
        shortcut.Description = "HexChat - P2P Voice and Text Chat Application"
        shortcut.IconLocation = str(hexchat_path / "icon.ico")  # Optional icon
        shortcut.WindowStyle = 1  # Normal window
        shortcut.save()
        
        print(f"✓ Desktop shortcut created successfully")
        print(f"  Location: {shortcut_path}")
        print(f"  Target: {batch_file}")
        return True
    except Exception as e:
        print(f"ERROR: Could not create shortcut: {e}")
        return False


def create_powershell_shortcut():
    """Create a shortcut using PowerShell (alternative method)."""
    hexchat_path = get_hexchat_path()
    if not hexchat_path:
        print("ERROR: Could not find HexChat installation")
        return False
    
    # Create batch launcher
    batch_file = create_batch_launcher(hexchat_path)
    if not batch_file:
        print("ERROR: Could not create batch launcher")
        return False
    
    desktop_path = Path.home() / "Desktop"
    shortcut_path = desktop_path / "HexChat.lnk"
    
    ps_script = f"""
$DesktopPath = [System.IO.Path]::Combine($env:USERPROFILE, "Desktop")
$ShortcutPath = [System.IO.Path]::Combine($DesktopPath, "HexChat.lnk")
$TargetPath = "{batch_file}"
$WorkingDirectory = "{hexchat_path}"

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)

$Shortcut.TargetPath = $TargetPath
$Shortcut.WorkingDirectory = $WorkingDirectory
$Shortcut.Description = "HexChat - P2P Voice and Text Chat Application"
$Shortcut.WindowStyle = 1

$Shortcut.Save()

Write-Host "✓ Desktop shortcut created successfully at: $ShortcutPath"
"""
    
    try:
        import subprocess
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"✓ Desktop shortcut created successfully")
            print(f"  Location: {shortcut_path}")
            return True
        else:
            print(f"ERROR: {result.stderr}")
            return False
    except Exception as e:
        print(f"ERROR: Could not create shortcut: {e}")
        return False


def main():
    """Main entry point."""
    print("=" * 50)
    print("HexChat Shortcut Generator")
    print("=" * 50)
    print()
    
    hexchat_path = get_hexchat_path()
    if hexchat_path:
        print(f"Found HexChat at: {hexchat_path}")
        print()
    else:
        print("ERROR: HexChat not found in standard locations")
        print("Please specify the path manually")
        return False
    
    # Try win32com first, fall back to PowerShell
    print("Creating desktop shortcut...")
    if not create_windows_shortcut():
        print("\nTrying alternative method with PowerShell...")
        if not create_powershell_shortcut():
            print("\nFailed to create shortcut")
            return False
    
    print("\nShortcut creation complete!")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
