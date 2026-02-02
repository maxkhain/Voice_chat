@echo off
echo ============================================================
echo Building HexChat Executable
echo ============================================================
echo.

REM Check if PyInstaller is installed
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
    if errorlevel 1 (
        echo.
        echo ERROR: Failed to install PyInstaller
        echo Please run: pip install pyinstaller
        pause
        exit /b 1
    )
)

echo Building executable...
echo.
python build_executable.py

if errorlevel 1 (
    echo.
    echo Build failed! Check error messages above.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo Build Complete!
echo ============================================================
echo.
echo Executable created at: dist\HexChat.exe
echo.
echo Would you like to create a desktop shortcut? (Y/N)
set /p create_shortcut=

if /i "%create_shortcut%"=="Y" (
    echo.
    echo Creating desktop shortcut...
    powershell -ExecutionPolicy Bypass -File create_desktop_shortcut.ps1
    echo.
    echo Done! Look for HexChat icon on your desktop.
) else (
    echo.
    echo Skipping shortcut creation.
    echo To create it later, run: create_desktop_shortcut.ps1
)

echo.
echo Press any key to exit...
pause >nul
