@echo off
REM HexChat P2P Voice/Chat Application
REM This batch file runs the HexChat application

cd /d "c:\Users\max\Documents\Local_voice\Voice_chat"

REM Run the Python application
python main.py

REM Pause to show any error messages
if errorlevel 1 pause
