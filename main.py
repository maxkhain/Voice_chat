# main_flet.py
"""
Main entry point for HexChat Flet app (Cross-platform: Windows, Android, iOS, Web)
Integrates UI layout with backend logic for P2P voice chat.
"""
import flet as ft
from ui_modules.ui_layout_flet import HexChatFletLayout
from ui_modules.ui_backend_flet import HexChatBackend
from config.contacts import get_contacts_display_list, extract_ip_from_contact_display


def main(page: ft.Page):
    """Main function for Flet app."""
    # Load and apply saved settings
    from config.app_settings import load_settings
    from audio_modules.sound_effects import (
        set_call_volume, set_message_incoming_volume,
        set_message_outgoing_volume, set_incoming_voice_volume,
        set_sound_effects_volume
    )
    
    saved_settings = load_settings()
    volumes = saved_settings.get("volumes", {})
    
    # Apply saved volumes (convert from 0-100 to 0.0-1.0)
    if volumes:
        set_call_volume(volumes.get("call", 70) / 100.0)
        set_message_incoming_volume(volumes.get("message_incoming", 60) / 100.0)
        set_message_outgoing_volume(volumes.get("message_outgoing", 50) / 100.0)
        set_incoming_voice_volume(volumes.get("incoming_voice", 100) / 100.0)
        set_sound_effects_volume(volumes.get("sound_effects", 50) / 100.0)
        print(f"[OK] Loaded saved settings: volumes={volumes}")
    
    # Create UI layout
    layout = HexChatFletLayout(page)
    
    # Create backend and link to layout
    backend = HexChatBackend(layout)
    
    # Wire up event handlers
    layout.on_connect_click = backend.connect
    layout.on_disconnect_click = backend.disconnect
    layout.on_send_message = backend.send_message
    layout.on_mute_toggle = backend.toggle_mute
    layout.on_deafen_toggle = backend.toggle_deafen
    
    def handle_contact_selected(contact_display):
        """Handle contact selection from dropdown."""
        ip = extract_ip_from_contact_display(contact_display)
        if ip:
            backend.select_contact(contact_display)
    
    def handle_device_selected(ip_address):
        """Handle device selection from network scanner."""
        backend.target_ip = ip_address
        layout.add_system_message("General", f"📌 Selected from scanner: {ip_address}")
        page.update()
    
    def handle_refresh_contacts():
        """Refresh the contacts list."""
        backend.refresh_contacts()
    
    layout.on_contact_selected = handle_contact_selected
    layout.on_device_selected = handle_device_selected
    layout.on_refresh_contacts = handle_refresh_contacts
    
    # Load sound effects
    try:
        from audio_modules.sound_effects import get_available_sounds
        available_sounds = get_available_sounds()
        
        def play_sound(sound_name, category):
            """Play a sound effect."""
            from audio_modules.sound_effects import play_custom_sound
            try:
                play_custom_sound(sound_name, category)
                layout.add_system_message("General", f"🔊 Played: {sound_name}")
                page.update()
            except Exception as e:
                print(f"Error playing sound: {e}")
        
        # Add sound buttons from special categories only (exclude 'basic')
        for category, sounds in available_sounds.items():
            # Skip basic/default sounds
            if category.lower() == 'basic':
                continue
            
            for sound_info in sounds[:10]:  # Add first 10 from each special category
                sound_name = sound_info['name']
                
                # Get emoji based on sound name
                emoji = "🔊"
                name_lower = sound_name.lower()
                if "clap" in name_lower:
                    emoji = "👏"
                elif "laugh" in name_lower:
                    emoji = "😂"
                elif "horn" in name_lower or "air" in name_lower:
                    emoji = "📢"
                elif "drum" in name_lower:
                    emoji = "🥁"
                elif "wow" in name_lower:
                    emoji = "😮"
                elif "hello" in name_lower or "hi" in name_lower:
                    emoji = "👋"
                elif "sad" in name_lower:
                    emoji = "😢"
                elif "happy" in name_lower:
                    emoji = "😊"
                
                layout.add_sound_button(sound_name, emoji, lambda sn=sound_name, cat=category: play_sound(sn, cat))
    except Exception as e:
        print(f"Could not load sound effects: {e}")
        import traceback
        traceback.print_exc()
    
    # Load initial contacts
    contacts = get_contacts_display_list()
    layout.update_contacts_list(contacts)
    
    # Welcome message
    layout.add_system_message("General", "🎉 Welcome to HexChat P2P!")
    layout.add_system_message(
        "General",
        "💡 Tip: Use 'Scan Network' to find devices or 'Add Friend' to save contacts"
    )
    
    page.update()


if __name__ == "__main__":
    # Run as desktop app
    ft.run(main)
    
    # To build for Android:
    # 1. Install: pip install flet
    # 2. Build APK: flet build apk
    # 3. Build AAB: flet build aab
    #
    # To build for iOS:
    # flet build ipa
    #
    # To build for Web:
    # flet build web

    # 1. Install: pip install flet
    # 2. Run: flet build apk
    # 3. Find APK in: build/apk/
