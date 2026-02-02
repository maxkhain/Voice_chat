# Create Desktop Shortcut for HexChat Executable
$DesktopPath = [System.IO.Path]::Combine($env:USERPROFILE, "Desktop")
$ShortcutPath = [System.IO.Path]::Combine($DesktopPath, "HexChat.lnk")
$TargetPath = "c:\Users\max\Documents\Local_voice\Voice_chat\dist\HexChat.exe"
$WorkingDirectory = "c:\Users\max\Documents\Local_voice\Voice_chat"
$IconPath = "c:\Users\max\Documents\Local_voice\Voice_chat\hexchat.ico"

# Check if executable exists
if (-Not (Test-Path $TargetPath)) {
    Write-Host "ERROR: HexChat.exe not found at: $TargetPath" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please build the executable first by running:" -ForegroundColor Yellow
    Write-Host "  python build_executable.py" -ForegroundColor Cyan
    Write-Host ""
    exit 1
}

# Create WScript.Shell object
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)

# Set shortcut properties
$Shortcut.TargetPath = $TargetPath
$Shortcut.WorkingDirectory = $WorkingDirectory
$Shortcut.Description = "HexChat - P2P Voice and Text Chat Application"
$Shortcut.WindowStyle = 1  # Normal window

# Set icon if it exists
if (Test-Path $IconPath) {
    $Shortcut.IconLocation = "$IconPath,0"
}

# Save the shortcut
$Shortcut.Save()

Write-Host "=" * 60 -ForegroundColor Green
Write-Host "Desktop shortcut created successfully!" -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Green
Write-Host ""
Write-Host "Shortcut Name: HexChat" -ForegroundColor Cyan
Write-Host "Location: $ShortcutPath" -ForegroundColor Cyan
Write-Host "Target: $TargetPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "You can now double-click the HexChat icon on your desktop to run the app!" -ForegroundColor Yellow
