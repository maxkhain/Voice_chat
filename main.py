"""
Main application entry point for Local Voice Chat.

Launches the GUI application.
"""
from ui import DiscordApp


if __name__ == "__main__":
    app = DiscordApp()
    app.mainloop()
