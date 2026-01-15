$DesktopPath = [System.IO.Path]::Combine($env:USERPROFILE, "Desktop")
$ShortcutPath = [System.IO.Path]::Combine($DesktopPath, "HexChat.lnk")
$TargetPath = "c:\Users\max\Documents\Local_voice\Voice_chat\run_hexchat.bat"
$WorkingDirectory = "c:\Users\max\Documents\Local_voice\Voice_chat"

# Create WScript.Shell object
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)

# Set shortcut properties
$Shortcut.TargetPath = $TargetPath
$Shortcut.WorkingDirectory = $WorkingDirectory
$Shortcut.Description = "HexChat - P2P Voice and Text Chat Application"
$Shortcut.WindowStyle = 1  # Normal window

# Save the shortcut
$Shortcut.Save()

Write-Host "Desktop shortcut created successfully at: $ShortcutPath"
Write-Host "Shortcut Name: HexChat"
