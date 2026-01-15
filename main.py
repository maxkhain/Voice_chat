"""
Main application entry point for Local Voice Chat.

Launches the GUI application.
"""
from ui_modules.ui import HexChatApp


if __name__ == "__main__":
    app = HexChatApp()
    app.mainloop()
