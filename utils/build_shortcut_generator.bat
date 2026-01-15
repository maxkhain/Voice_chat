@echo off
REM Build script for HexChat Shortcut Generator
REM Creates a standalone executable

echo Building HexChat Shortcut Generator...
echo.

REM Check if PyInstaller is installed
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

REM Check if pywin32 is installed
pip show pywin32 >nul 2>&1
if errorlevel 1 (
    echo Installing pywin32...
    pip install pywin32
)

REM Build the executable
echo.
echo Creating executable...
pyinstaller --onefile ^
    --windowed ^
    --name HexChatShortcutGenerator ^
    --icon NONE ^
    --add-data "shortcut_generator.py:." ^
    shortcut_generator.py

echo.
if exist dist\HexChatShortcutGenerator.exe (
    echo ✓ Build successful!
    echo Executable location: dist\HexChatShortcutGenerator.exe
    echo.
    echo You can now:
    echo 1. Run the executable directly
    echo 2. Create a shortcut to it on the desktop
    echo 3. Distribute it to other machines
) else (
    echo ✗ Build failed
    exit /b 1
)

pause
