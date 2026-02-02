# ui_layout_flet.py
"""
Flet UI Layout for HexChat - Cross-platform (Windows, Android, iOS, Web)
Discord-inspired dark theme design
"""
import flet as ft
from typing import Callable, Optional


# Discord-inspired color scheme
class Colors:
    # Background colors
    BG_PRIMARY = "#36393f"      # Main background
    BG_SECONDARY = "#2f3136"    # Sidebar background
    BG_TERTIARY = "#202225"     # Darker elements
    BG_ACCENT = "#40444b"       # Input fields
    
    # Text colors
    TEXT_PRIMARY = "#ffffff"
    TEXT_SECONDARY = "#b9bbbe"
    TEXT_MUTED = "#72767d"
    
    # Accent colors
    ACCENT_PRIMARY = "#5865f2"  # Discord blurple
    ACCENT_SUCCESS = "#3ba55d"  # Green
    ACCENT_DANGER = "#ed4245"   # Red
    ACCENT_WARNING = "#faa61a"  # Orange
    
    # Interactive colors
    HOVER = "#4e5058"
    ACTIVE = "#5865f2"


class HexChatFletLayout:
    """Base class for Flet UI layout with Discord-inspired styling."""
    
    def __init__(self, page: ft.Page):
        self.page = page
        
        # Setup page properties
        self._setup_page()
        
        # State variables
        self.current_chat_ip = None
        self.chat_tabs = {}  # {ip: tab}
        self.emoji_panel_visible = False
        
        # Event callbacks (to be overridden by logic class)
        self.on_settings_click: Optional[Callable] = None
        self.on_contact_selected: Optional[Callable] = None
        self.on_add_contact_click: Optional[Callable] = None
        self.on_connect_click: Optional[Callable] = None
        self.on_disconnect_click: Optional[Callable] = None
        self.on_mute_toggle: Optional[Callable] = None
        self.on_deafen_toggle: Optional[Callable] = None
        self.on_send_message: Optional[Callable] = None
        self.on_emoji_toggle: Optional[Callable] = None
        self.on_scan_network_click: Optional[Callable] = None
        self.on_device_selected: Optional[Callable] = None
        self.on_settings_save: Optional[Callable] = None
        self.on_refresh_contacts: Optional[Callable] = None
        
        # Build UI
        self._build_ui()
    
    def _setup_page(self):
        """Configure page properties."""
        self.page.title = "HexChat P2P"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.bgcolor = Colors.BG_PRIMARY
        self.page.padding = 0
        
        # Set window size for desktop
        self.page.window_width = 1400
        self.page.window_height = 900
        self.page.window_min_width = 800
        self.page.window_min_height = 600
    
    def _build_ui(self):
        """Build the main UI layout."""
        # Main layout: Row with sidebar and chat area
        self.main_row = ft.Row(
            controls=[
                self._build_sidebar(),
                ft.VerticalDivider(width=1, color=Colors.BG_TERTIARY),
                self._build_chat_area(),
            ],
            spacing=0,
            expand=True,
        )
        
        self.page.add(self.main_row)
    
    def _build_sidebar(self) -> ft.Container:
        """Build the sidebar with controls."""
        # Logo
        logo = ft.Container(
            content=ft.Text(
                "HEXCHAT P2P",
                size=20,
                weight=ft.FontWeight.BOLD,
                color=Colors.TEXT_PRIMARY,
            ),
            padding=ft.padding.all(15),
            alignment=ft.alignment.Alignment(0, 0),  # Center alignment
        )
        
        # Settings button
        self.settings_btn = ft.ElevatedButton(
            "⚙️ Settings",
            on_click=lambda _: self.show_settings_dialog(),
            bgcolor=Colors.BG_ACCENT,
            color=Colors.TEXT_PRIMARY,
            width=220,
        )
        
        # Contacts section
        contacts_label = ft.Text(
            "Saved Contacts:",
            size=12,
            weight=ft.FontWeight.BOLD,
            color=Colors.TEXT_SECONDARY,
        )
        
        self.contacts_dropdown = ft.Dropdown(
            width=220,
            bgcolor=Colors.BG_ACCENT,
            color=Colors.TEXT_PRIMARY,
            border_color=Colors.BG_ACCENT,
        )
        self.contacts_dropdown.on_change = lambda e: self.on_contact_selected(e.control.value) if self.on_contact_selected else None
        
        self.add_contact_btn = ft.ElevatedButton(
            "➕ Add Friend",
            on_click=lambda _: self.show_add_friend_dialog(),
            bgcolor=Colors.BG_ACCENT,
            color=Colors.TEXT_PRIMARY,
            width=220,
        )
        
        self.scan_network_btn = ft.ElevatedButton(
            "🔍 Scan Network",
            on_click=lambda _: self.show_network_scanner_dialog(),
            bgcolor=Colors.ACCENT_PRIMARY,
            color=Colors.TEXT_PRIMARY,
            width=220,
        )
        
        # Connection buttons
        self.connect_btn = ft.ElevatedButton(
            "Connect Voice/Chat",
            on_click=lambda _: self.on_connect_click() if self.on_connect_click else None,
            bgcolor=Colors.ACCENT_SUCCESS,
            color=Colors.TEXT_PRIMARY,
            width=220,
        )
        
        self.disconnect_btn = ft.ElevatedButton(
            "Disconnect",
            on_click=lambda _: self.on_disconnect_click() if self.on_disconnect_click else None,
            bgcolor=Colors.ACCENT_DANGER,
            color=Colors.TEXT_PRIMARY,
            width=220,
            disabled=True,
        )
        
        # Voice controls
        self.mute_switch = ft.Switch(
            label="Mute Mic",
            label_text_style=ft.TextStyle(color=Colors.TEXT_SECONDARY),
            active_color=Colors.ACCENT_DANGER,
            on_change=lambda _: self.on_mute_toggle() if self.on_mute_toggle else None,
        )
        
        self.deafen_switch = ft.Switch(
            label="Deafen Audio",
            label_text_style=ft.TextStyle(color=Colors.TEXT_SECONDARY),
            active_color=Colors.ACCENT_DANGER,
            on_change=lambda _: self.on_deafen_toggle() if self.on_deafen_toggle else None,
        )
        
        # Sidebar content
        sidebar_content = ft.Column(
            controls=[
                logo,
                ft.Divider(height=1, color=Colors.BG_TERTIARY),
                ft.Container(content=self.settings_btn, padding=ft.padding.symmetric(horizontal=10, vertical=5)),
                ft.Container(
                    content=ft.Column([
                        contacts_label,
                        self.contacts_dropdown,
                        self.add_contact_btn,
                        self.scan_network_btn,
                    ], spacing=5),
                    padding=ft.padding.all(10),
                ),
                ft.Divider(height=1, color=Colors.BG_TERTIARY),
                ft.Container(content=self.connect_btn, padding=ft.padding.symmetric(horizontal=10, vertical=5)),
                ft.Container(content=self.disconnect_btn, padding=ft.padding.symmetric(horizontal=10, vertical=5)),
                ft.Divider(height=1, color=Colors.BG_TERTIARY),
                ft.Container(
                    content=ft.Column([
                        self.mute_switch,
                        self.deafen_switch,
                    ], spacing=10),
                    padding=ft.padding.all(10),
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
            spacing=0,
        )
        
        return ft.Container(
            content=sidebar_content,
            width=250,
            bgcolor=Colors.BG_SECONDARY,
            expand=False,
        )
    
    def _build_chat_area(self) -> ft.Container:
        """Build the main chat area."""
        # Initialize General tab in chat_tabs dict
        general_tab = self._build_chat_tab("General")
        self.chat_tabs["General"] = general_tab
        
        # Wrap in container so we can switch content
        self.chat_content = ft.Container(
            content=general_tab,
            expand=True,
        )
        
        # Tab bar with channel selector
        tab_bar = ft.Container(
            content=ft.Row([
                ft.TextButton(
                    "💬 General",
                    style=ft.ButtonStyle(
                        color=Colors.TEXT_PRIMARY,
                        bgcolor=Colors.BG_ACCENT,
                    ),
                ),
            ]),
            bgcolor=Colors.BG_SECONDARY,
            padding=10,
        )
        
        # Message input area
        self.chat_target_dropdown = ft.Dropdown(
            label="Chat with:",
            width=150,
            bgcolor=Colors.BG_ACCENT,
            color=Colors.TEXT_PRIMARY,
            border_color=Colors.BG_ACCENT,
            options=[ft.dropdown.Option("General")],
        )
        # Add on_change handler for switching chat tabs
        self.chat_target_dropdown.on_change = lambda e: self.switch_to_chat_tab(e.control.value)
        
        self.message_input = ft.TextField(
            hint_text="Type message...",
            bgcolor=Colors.BG_ACCENT,
            color=Colors.TEXT_PRIMARY,
            border_color=Colors.BG_ACCENT,
            expand=True,
            on_submit=lambda _: self.on_send_message() if self.on_send_message else None,
        )
        
        self.emoji_btn = ft.Container(
            content=ft.Text("😊", size=24),
            width=40,
            height=40,
            border_radius=5,
            bgcolor=Colors.BG_ACCENT,
            alignment=ft.alignment.Alignment(0, 0),
            on_click=lambda _: self.show_emoji_picker(),
            ink=True,
        )
        
        self.send_btn = ft.ElevatedButton(
            "Send",
            on_click=lambda _: self.on_send_message() if self.on_send_message else None,
            bgcolor=Colors.ACCENT_PRIMARY,
            color=Colors.TEXT_PRIMARY,
        )
        
        input_row = ft.Row(
            controls=[
                self.chat_target_dropdown,
                self.message_input,
                self.emoji_btn,
                self.send_btn,
            ],
            spacing=10,
        )
        
        # Sound effects panel placeholder
        self.sound_effects_row = ft.Row(
            controls=[],
            scroll=ft.ScrollMode.AUTO,
            spacing=5,
        )
        
        # Chat area layout
        chat_content = ft.Column(
            controls=[
                tab_bar,
                ft.Container(
                    content=self.chat_content,
                    expand=True,
                ),
                ft.Divider(height=1, color=Colors.BG_TERTIARY),
                ft.Container(
                    content=self.sound_effects_row,
                    padding=ft.padding.all(10),
                    bgcolor=Colors.BG_SECONDARY,
                ),
                ft.Container(
                    content=input_row,
                    padding=ft.padding.all(10),
                    bgcolor=Colors.BG_SECONDARY,
                ),
            ],
            spacing=0,
            expand=True,
        )
        
        return ft.Container(
            content=chat_content,
            bgcolor=Colors.BG_PRIMARY,
            expand=True,
        )
    
    def _build_chat_tab(self, tab_name: str) -> ft.Column:
        """Build a chat tab with message list and scrolling."""
        chat_list = ft.ListView(
            spacing=5,
            padding=10,
            auto_scroll=True,
            expand=True,
        )
        
        # Store reference
        self.chat_tabs[tab_name] = chat_list
        
        return ft.Column(
            controls=[chat_list],
            expand=True,
        )
    
    def add_message_to_chat(self, tab_name: str, sender: str, message: str, timestamp: str):
        """Add a message to a specific chat tab."""
        if tab_name not in self.chat_tabs:
            return
        
        # Format timestamp
        time_str = timestamp.split("T")[1][:8] if "T" in timestamp else timestamp
        
        # Message bubble
        message_content = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(sender, weight=ft.FontWeight.BOLD, color=Colors.ACCENT_PRIMARY, size=14),
                    ft.Text(time_str, color=Colors.TEXT_MUTED, size=11),
                ], spacing=10),
                ft.Text(message, color=Colors.TEXT_PRIMARY, size=14),
            ], spacing=3),
            bgcolor=Colors.BG_SECONDARY,
            padding=10,
            border_radius=5,
        )
        
        self.chat_tabs[tab_name].controls.append(message_content)
        self.page.update()
    
    def add_system_message(self, tab_name: str, message: str):
        """Add a system message to chat."""
        if tab_name not in self.chat_tabs:
            return
        
        system_msg = ft.Container(
            content=ft.Text(
                message,
                color=Colors.TEXT_MUTED,
                size=13,
                italic=True,
            ),
            padding=5,
            alignment=ft.alignment.Alignment(0, 0),  # Center alignment
        )
        
        self.chat_tabs[tab_name].controls.append(system_msg)
        self.page.update()
    
    def add_sound_button(self, sound_name: str, icon: str, callback: Callable):
        """Add a sound effect button."""
        btn = ft.Container(
            content=ft.Text(icon, size=32),
            width=70,
            height=70,
            bgcolor=Colors.BG_ACCENT,
            border_radius=10,
            alignment=ft.alignment.Alignment(0, 0),  # Center alignment
            on_click=lambda _: callback(sound_name),
            ink=True,
        )
        
        self.sound_effects_row.controls.append(btn)
        self.page.update()
    
    def show_dialog(self, title: str, content: str, actions: list = None):
        """Show a dialog box."""
        def close_dlg(e):
            dialog.open = False
            self.page.update()
        
        if actions is None:
            actions = [
                ft.TextButton("OK", on_click=close_dlg)
            ]
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(title),
            content=ft.Text(content),
            actions=actions,
        )
        
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
    
    def show_emoji_picker(self):
        """Show emoji picker dialog."""
        print("[DEBUG] Opening emoji picker...")
        
        emojis = [
            "😀", "😃", "😄", "😁", "😆", "😅", "🤣", "😂",
            "😊", "😇", "🙂", "🙃", "😉", "😌", "😍", "🥰",
            "😘", "😗", "😙", "😚", "😋", "😛", "😝", "😜",
            "🤪", "🤨", "🧐", "🤓", "😎", "🤩", "🥳", "😏",
            "👍", "👎", "👏", "🙌", "👐", "🤝", "🙏", "✌️",
            "🤞", "🤟", "🤘", "🤙", "👋", "🤚", "🖐️", "✋",
            "❤️", "🧡", "💛", "💚", "💙", "💜", "🤎", "🖤",
            "🔥", "✨", "💫", "⭐", "🌟", "💥", "💢", "💯"
        ]
        
        def insert_emoji(e, emoji):
            current = self.message_input.value or ""
            self.message_input.value = current + emoji
            dlg.open = False
            self.page.update()
        
        def close_dlg(e):
            dlg.open = False
            self.page.update()
        
        emoji_buttons = []
        for emoji in emojis:
            btn = ft.Container(
                content=ft.Text(emoji, size=24),
                width=50,
                height=50,
                alignment=ft.alignment.Alignment(0, 0),
                on_click=lambda e, em=emoji: insert_emoji(e, em),
                ink=True,
                border_radius=5,
            )
            emoji_buttons.append(btn)
        
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Select Emoji", size=20, weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Column([
                    ft.Row(
                        emoji_buttons[i:i+8],
                        wrap=True,
                        spacing=5,
                    ) for i in range(0, len(emoji_buttons), 8)
                ], scroll=ft.ScrollMode.AUTO, spacing=5),
                width=450,
                height=400,
                padding=10,
            ),
            actions=[
                ft.TextButton("Close", on_click=close_dlg),
            ],
        )
        
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()
        print("[DEBUG] Emoji picker opened")
    
    def update_contacts_list(self, contacts: list):
        """Update the contacts dropdown and chat target dropdown."""
        self.contacts_dropdown.options = [
            ft.dropdown.Option(contact) for contact in contacts
        ]
        # Also update chat target dropdown with contacts
        chat_options = [ft.dropdown.Option("General")]
        chat_options.extend([ft.dropdown.Option(contact) for contact in contacts])
        self.chat_target_dropdown.options = chat_options
        self.page.update()
    
    def switch_to_chat_tab(self, contact_display: str):
        """Switch to or create a chat tab for the specified contact."""
        print(f"[DEBUG] Switching to chat: {contact_display}")
        
        if contact_display == "General":
            self.current_chat_ip = None
            # Switch to general chat
            self.chat_content.content = self.chat_tabs.get("General", ft.Column([]))
            self.page.update()
            return
        
        # Extract IP from contact display
        from config.contacts import extract_ip_from_contact_display, get_contact_name
        ip = extract_ip_from_contact_display(contact_display)
        
        if not ip:
            print(f"[DEBUG] No IP found for: {contact_display}")
            return
        
        print(f"[DEBUG] Extracted IP: {ip}")
        
        # Create new tab if doesn't exist and load history
        if ip not in self.chat_tabs:
            new_tab = ft.Column(
                controls=[],
                spacing=5,
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            )
            self.chat_tabs[ip] = new_tab
            
            # Load chat history
            try:
                from config.chat_history import load_history
                history = load_history(ip)
                if history:
                    for msg in history:
                        sender = msg.get('sender', 'Unknown')
                        text = msg.get('message', '')
                        timestamp = msg.get('timestamp', '')
                        self.add_message_to_chat(ip, sender, text, timestamp)
                    print(f"[DEBUG] Loaded {len(history)} messages from history")
            except Exception as e:
                print(f"[DEBUG] Error loading history: {e}")
        
        # Switch current chat
        self.current_chat_ip = ip
        self.chat_content.content = self.chat_tabs[ip]
        
        # Update chat_target_dropdown to reflect the switch
        self.chat_target_dropdown.value = contact_display
        
        self.page.update()
        
        # Add system message to General about switching
        contact_name = get_contact_name(ip)
        display = contact_name if contact_name else ip
        self.add_system_message("General", f"💬 Now chatting with: {display}")
        print(f"[DEBUG] Switched to chat with {display}, chat_tabs has {len(self.chat_tabs[ip].controls)} messages")
    # ==================== DIALOG FUNCTIONS ====================
    def show_settings_dialog(self):
        """Show settings dialog for audio devices and volumes."""
        print("[DEBUG] Opening settings dialog...")
        from audio_modules.audio_io import get_audio_interface, get_input_devices, get_output_devices
        from audio_modules.sound_effects import (
            get_call_volume, get_message_incoming_volume,
            get_message_outgoing_volume, get_incoming_voice_volume,
            get_sound_effects_volume
        )
        from config.app_settings import load_settings, save_settings as save_app_settings
        
        # Load saved settings
        saved_settings = load_settings()
        volumes = saved_settings.get("volumes", {})
        
        # Get available devices
        try:
            p = get_audio_interface()
            input_devices_raw = get_input_devices(p)
            output_devices_raw = get_output_devices(p)
            
            # Convert to dict format for dropdown
            input_devices = [{'index': idx, 'name': name} for idx, name in input_devices_raw]
            output_devices = [{'index': idx, 'name': name} for idx, name in output_devices_raw]
            
            p.terminate()
        except Exception as e:
            input_devices = []
            output_devices = []
            print(f"Error getting devices: {e}")
        
        # Volume sliders with divisions for integer steps
        call_vol_slider = ft.Slider(
            min=0,
            max=100,
            divisions=100,
            value=volumes.get("call", int(get_call_volume() * 100)),
            label="Call: {value}%",
            width=300,
            on_change=lambda e: self.page.update(),
        )
        
        msg_in_vol_slider = ft.Slider(
            min=0,
            max=100,
            divisions=100,
            value=volumes.get("message_incoming", int(get_message_incoming_volume() * 100)),
            label="Msg In: {value}%",
            width=300,
            on_change=lambda e: self.page.update(),
        )
        
        msg_out_vol_slider = ft.Slider(
            min=0,
            max=100,
            divisions=100,
            value=volumes.get("message_outgoing", int(get_message_outgoing_volume() * 100)),
            label="Msg Out: {value}%",
            width=300,
            on_change=lambda e: self.page.update(),
        )
        
        voice_vol_slider = ft.Slider(
            min=0,
            max=100,
            divisions=100,
            value=volumes.get("incoming_voice", int(get_incoming_voice_volume() * 100)),
            label="Voice: {value}%",
            width=300,
            on_change=lambda e: self.page.update(),
        )
        
        sfx_vol_slider = ft.Slider(
            min=0,
            max=100,
            divisions=100,
            value=volumes.get("sound_effects", int(get_sound_effects_volume() * 100)),
            label="SFX: {value}%",
            width=300,
            on_change=lambda e: self.page.update(),
        )
        
        # Microphone dropdown
        mic_dropdown = ft.Dropdown(
            label="Microphone",
            options=[ft.dropdown.Option(f"{d['index']}: {d['name']}") for d in input_devices],
            width=400,
            bgcolor=Colors.BG_ACCENT,
        )
        
        # Speaker dropdown
        speaker_dropdown = ft.Dropdown(
            label="Speaker",
            options=[ft.dropdown.Option(f"{d['index']}: {d['name']}") for d in output_devices],
            width=400,
            bgcolor=Colors.BG_ACCENT,
        )
        
        def close_dlg(e):
            dlg.open = False
            self.page.update()
        
        def save_settings(e):
            from audio_modules.sound_effects import (
                set_call_volume, set_message_incoming_volume,
                set_message_outgoing_volume, set_incoming_voice_volume,
                set_sound_effects_volume
            )
            
            # Debug: print slider values
            # Force page update to ensure slider values are current
            self.page.update()
            
            print(f"[DEBUG] Slider values - Call: {call_vol_slider.value}, Msg In: {msg_in_vol_slider.value}, Msg Out: {msg_out_vol_slider.value}, Voice: {voice_vol_slider.value}, SFX: {sfx_vol_slider.value}")
            
            # Save volumes (convert from 0-100 slider to 0.0-1.0)
            set_call_volume(call_vol_slider.value / 100.0)
            set_message_incoming_volume(msg_in_vol_slider.value / 100.0)
            set_message_outgoing_volume(msg_out_vol_slider.value / 100.0)
            set_incoming_voice_volume(voice_vol_slider.value / 100.0)
            set_sound_effects_volume(sfx_vol_slider.value / 100.0)
            
            # Save to persistent storage
            settings_to_save = load_settings()
            settings_to_save["volumes"] = {
                "call": int(call_vol_slider.value),
                "message_incoming": int(msg_in_vol_slider.value),
                "message_outgoing": int(msg_out_vol_slider.value),
                "incoming_voice": int(voice_vol_slider.value),
                "sound_effects": int(sfx_vol_slider.value)
            }
            
            # Save device selections
            if mic_dropdown.value:
                try:
                    mic_index = int(mic_dropdown.value.split(":")[0])
                    settings_to_save["devices"]["microphone_index"] = mic_index
                except:
                    pass
            
            if speaker_dropdown.value:
                try:
                    speaker_index = int(speaker_dropdown.value.split(":")[0])
                    settings_to_save["devices"]["speaker_index"] = speaker_index
                except:
                    pass
            
            save_app_settings(settings_to_save)
            
            # Call callback if provided
            if self.on_settings_save:
                self.on_settings_save(mic_dropdown.value, speaker_dropdown.value)
            
            self.add_system_message("General", "✅ Settings saved")
            close_dlg(e)
        
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("⚙️ Settings", size=20, weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Audio Devices", size=16, weight=ft.FontWeight.BOLD),
                    mic_dropdown,
                    speaker_dropdown,
                    ft.Divider(height=20),
                    ft.Text("Volume Controls", size=16, weight=ft.FontWeight.BOLD),
                    ft.Row([ft.Text("Call Volume:", width=100), call_vol_slider]),
                    ft.Row([ft.Text("Message In:", width=100), msg_in_vol_slider]),
                    ft.Row([ft.Text("Message Out:", width=100), msg_out_vol_slider]),
                    ft.Row([ft.Text("Voice:", width=100), voice_vol_slider]),
                    ft.Row([ft.Text("Sound FX:", width=100), sfx_vol_slider]),
                ], spacing=10, scroll=ft.ScrollMode.AUTO),
                width=500,
                height=500,
                padding=20,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=close_dlg),
                ft.ElevatedButton(
                    "Save",
                    on_click=save_settings,
                    bgcolor=Colors.ACCENT_PRIMARY,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()
        print("[DEBUG] Settings dialog added to overlay and opened")
    
    def show_network_scanner_dialog(self):
        """Show network scanner dialog."""
        print("[DEBUG] Opening network scanner dialog...")
        from utils.network_scanner import scan_network_async, format_device_list, get_local_ip
        
        scan_result_list = ft.ListView(spacing=5, height=400)
        scan_button = ft.ElevatedButton("🔍 Scan Network", bgcolor=Colors.ACCENT_PRIMARY)
        progress_ring = ft.ProgressRing(visible=False)
        status_text = ft.Text("", color=Colors.TEXT_SECONDARY, size=14)
        
        def close_dlg(e):
            dlg.open = False
            self.page.update()
        
        def select_device(ip_address):
            """Select a scanned device."""
            if self.on_device_selected:
                self.on_device_selected(ip_address)
            self.add_system_message("General", f"📌 Selected: {ip_address}")
            close_dlg(None)
        
        def start_scan(e):
            scan_button.disabled = True
            progress_ring.visible = True
            status_text.value = "Scanning network..."
            scan_result_list.controls.clear()
            self.page.update()
            
            def scan_complete(devices):
                scan_button.disabled = False
                progress_ring.visible = False
                
                if devices:
                    status_text.value = f"Found {len(devices)} device(s)"
                    for device in devices:
                        ip = device.get('ip', 'Unknown')
                        hostname = device.get('hostname', 'Unknown')
                        
                        device_btn = ft.Container(
                            content=ft.Row([
                                ft.Text("💻", size=24),
                                ft.Column([
                                    ft.Text(hostname, weight=ft.FontWeight.BOLD),
                                    ft.Text(ip, size=12, color=Colors.TEXT_SECONDARY),
                                ], spacing=2),
                            ], spacing=10),
                            bgcolor=Colors.BG_ACCENT,
                            padding=10,
                            border_radius=5,
                            on_click=lambda e, ip=ip: select_device(ip),
                            ink=True,
                        )
                        scan_result_list.controls.append(device_btn)
                else:
                    status_text.value = "No devices found"
                
                self.page.update()
            
            # Run scan in background
            def run_scan():
                try:
                    devices = []
                    for device in scan_network_async():
                        devices.append(device)
                    scan_complete(devices)
                except Exception as e:
                    status_text.value = f"Error: {e}"
                    scan_button.disabled = False
                    progress_ring.visible = False
                    self.page.update()
            
            import threading
            threading.Thread(target=run_scan, daemon=True).start()
        
        scan_button.on_click = start_scan
        
        local_ip = get_local_ip()
        
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("🌐 Network Scanner", size=20, weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(f"Your IP: {local_ip}", size=14, color=Colors.ACCENT_PRIMARY),
                    ft.Row([scan_button, progress_ring], spacing=10),
                    status_text,
                    ft.Divider(),
                    ft.Text("Discovered Devices:", size=14, weight=ft.FontWeight.BOLD),
                    scan_result_list,
                ], spacing=10),
                width=500,
                padding=20,
            ),
            actions=[
                ft.TextButton("Close", on_click=close_dlg),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()
        print("[DEBUG] Network scanner dialog added to overlay")
    
    def show_add_friend_dialog(self):
        """Show add friend by IP dialog."""
        print("[DEBUG] Opening add friend dialog...")
        from config.contacts import add_contact
        
        name_field = ft.TextField(
            label="Friend Name",
            hint_text="Enter a friendly name",
            width=400,
            bgcolor=Colors.BG_ACCENT,
        )
        
        ip_field = ft.TextField(
            label="IP Address",
            hint_text="192.168.1.100",
            width=400,
            bgcolor=Colors.BG_ACCENT,
        )
        
        status_text = ft.Text("", color=Colors.TEXT_SECONDARY, size=14)
        
        def close_dlg(e):
            dlg.open = False
            self.page.update()
        
        def save_friend(e):
            name = name_field.value
            ip = ip_field.value
            
            if not name or not ip:
                status_text.value = "⚠️ Please fill in both fields"
                status_text.color = Colors.ACCENT_DANGER
                self.page.update()
                return
            
            # Validate IP format
            import re
            if not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
                status_text.value = "⚠️ Invalid IP address format"
                status_text.color = Colors.ACCENT_DANGER
                self.page.update()
                return
            
            try:
                add_contact(ip, name)
                status_text.value = f"✅ Added {name} ({ip})"
                status_text.color = Colors.ACCENT_SUCCESS
                self.page.update()
                
                # Refresh contacts list
                if self.on_refresh_contacts:
                    self.on_refresh_contacts()
                
                # Close after a short delay
                import time
                time.sleep(1)
                close_dlg(e)
            except Exception as ex:
                status_text.value = f"❌ Error: {ex}"
                status_text.color = Colors.ACCENT_DANGER
                self.page.update()
        
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("➕ Add Friend", size=20, weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Add a friend by entering their IP address", size=14),
                    name_field,
                    ip_field,
                    status_text,
                ], spacing=15),
                width=450,
                padding=20,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=close_dlg),
                ft.ElevatedButton(
                    "Add Friend",
                    on_click=save_friend,
                    bgcolor=Colors.ACCENT_PRIMARY,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()
        print("[DEBUG] Add friend dialog should be visible now")