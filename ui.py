# ui.py
import customtkinter as ctk
import threading
from audio_io import (
    get_audio_interface,
    get_input_devices,
    get_output_devices,
    open_input_stream,
    open_output_stream,
    close_stream,
    close_audio_interface
)
from audio_sender import send_audio, cleanup_sender, send_text_message
from audio_receiver import receive_audio, cleanup_receiver, set_text_message_callback, set_deafen_state, set_deafen_state, set_incoming_call_callback, reset_receiver_socket
from audio_filter import reset_noise_profile
from connection_cache import (
    get_last_connection,
    get_last_microphone,
    get_last_speaker,
    has_cached_connection,
    save_cache,
)
from chat_history import add_message, load_history, display_history, clear_history, get_formatted_message, format_timestamp, format_date_header, needs_date_separator
from network_scanner import scan_network_async, format_device_list, extract_ip_from_formatted
from sound_effects import sound_calling, sound_incoming, sound_connected, sound_rejected, sound_disconnected, sound_message, sound_cancelled, stop_all_sounds, set_call_volume, set_message_incoming_volume, set_message_outgoing_volume, get_call_volume, get_message_incoming_volume, get_message_outgoing_volume, get_fun_sounds, play_custom_sound, set_send_custom_sound_callback


# --- APPEARANCE ---
ctk.set_appearance_mode("Dark")  # Modes: "System", "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue", "green", "dark-blue"


class HexChatApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.audio_interface = None
        self.input_stream = None
        self.output_stream = None
        self.background_output_stream = None  # For background receiver
        self.target_ip = None
        self.is_muted = False
        self.is_deafened = False
        self.receiver_thread = None
        self.sender_thread = None
        self.is_connected = False
        self.selected_device_index = 0
        self.selected_output_device_index = None  # Use default if None
        self.incoming_call_ip = None  # Track incoming call request
        self.call_state = "idle"  # idle, calling, ringing, connected
        self.background_receiver_active = False  # Track background receiver
        
        # Load cached values
        last_ip = get_last_connection()
        last_mic = get_last_microphone()
        last_speaker = get_last_speaker()
        
        # Store last IP for later use
        self.last_loaded_ip = last_ip
        
        # Window Setup
        self.title("HexChat")
        self.geometry("1200x800")
        
        # Get screen dimensions and center window
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        window_width = 1200
        window_height = 800
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # --- LAYOUT GRID ---
        self.grid_columnconfigure(0, weight=0)  # Sidebar fixed width
        self.grid_columnconfigure(1, weight=1)  # Chat area expands
        self.grid_rowconfigure(0, weight=1)     # Content expands vertically

        # --- SIDEBAR (LEFT) with Scrollbar ---
        self.sidebar_frame = ctk.CTkFrame(self, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.sidebar_frame.grid_rowconfigure(0, weight=1)
        
        # Scrollable sidebar
        self.sidebar = ctk.CTkScrollableFrame(self.sidebar_frame, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        self.logo_label = ctk.CTkLabel(self.sidebar, text="HEXCHAT P2P", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.pack(pady=20)

        # Device Selection
        self.device_label = ctk.CTkLabel(self.sidebar, text="Microphone:", font=ctk.CTkFont(size=12))
        self.device_label.pack(pady=(10, 5), padx=10)
        
        self.device_combo = ctk.CTkComboBox(
            self.sidebar,
            values=[],
            state="readonly",
            command=self.on_device_selected
        )
        self.device_combo.pack(pady=(0, 10), padx=10, fill="x")
        
        # Populate device list and select cached device
        self.populate_devices(last_mic)

        # Output Device Selection
        self.output_label = ctk.CTkLabel(self.sidebar, text="Speaker:", font=ctk.CTkFont(size=12))
        self.output_label.pack(pady=(10, 5), padx=10)
        
        self.output_combo = ctk.CTkComboBox(
            self.sidebar,
            values=[],
            state="readonly",
            command=self.on_output_device_selected
        )
        self.output_combo.pack(pady=(0, 10), padx=10, fill="x")
        
        # Populate output device list
        self.populate_output_devices(last_speaker)

        # Network Scan Section
        self.scan_label = ctk.CTkLabel(self.sidebar, text="Available PCs:", font=ctk.CTkFont(size=12))
        self.scan_label.pack(pady=(15, 5), padx=10)
        
        self.scan_btn = ctk.CTkButton(self.sidebar, text="Scan Network", command=self.start_network_scan)
        self.scan_btn.pack(pady=5, padx=10, fill="x")
        
        self.device_list = ctk.CTkComboBox(
            self.sidebar,
            values=[],
            state="readonly",
            command=self.on_device_selected_from_list
        )
        self.device_list.pack(pady=(0, 10), padx=10, fill="x")

        # IP Input with cached value
        self.ip_entry = ctk.CTkEntry(self.sidebar, placeholder_text="Enter Friend's IP")
        if last_ip:
            self.ip_entry.insert(0, last_ip)
        self.ip_entry.pack(pady=10, padx=10)

        # Connect Button
        self.connect_btn = ctk.CTkButton(self.sidebar, text="Connect Voice/Chat", command=self.connect)
        self.connect_btn.pack(pady=10, padx=10, fill="x")

        # Disconnect Button
        self.disconnect_btn = ctk.CTkButton(self.sidebar, text="Disconnect", command=self.disconnect, state="disabled")
        self.disconnect_btn.pack(pady=10, padx=10, fill="x")

        # Cancel Call Button (hidden by default)
        self.cancel_call_btn = ctk.CTkButton(self.sidebar, text="Cancel Call", command=self.cancel_call, state="disabled")
        self.cancel_call_btn.pack(pady=10, padx=10, fill="x")

        # Incoming Call Frame (hidden by default)
        self.call_frame = ctk.CTkFrame(self.sidebar)
        self.call_frame.pack(pady=10, padx=10, fill="x")
        self.call_frame.pack_forget()  # Hide initially

        self.call_label = ctk.CTkLabel(self.call_frame, text="📞 Incoming Call", font=ctk.CTkFont(size=12, weight="bold"))
        self.call_label.pack(pady=5)

        self.call_info_label = ctk.CTkLabel(self.call_frame, text="", font=ctk.CTkFont(size=10), wraplength=180)
        self.call_info_label.pack(pady=5)

        self.call_buttons_frame = ctk.CTkFrame(self.call_frame)
        self.call_buttons_frame.pack(pady=5, fill="x")

        self.accept_btn = ctk.CTkButton(self.call_buttons_frame, text="Accept", command=self.accept_call, width=80)
        self.accept_btn.pack(side="left", padx=5)

        self.reject_btn = ctk.CTkButton(self.call_buttons_frame, text="Reject", command=self.reject_call, width=80)
        self.reject_btn.pack(side="right", padx=5)

        # Voice Controls
        self.mute_btn = ctk.CTkSwitch(self.sidebar, text="Mute Mic", command=self.toggle_mute)
        self.mute_btn.pack(pady=20, padx=10)
        
        self.deafen_btn = ctk.CTkSwitch(self.sidebar, text="Deafen Audio", command=self.toggle_deafen)
        self.deafen_btn.pack(pady=5, padx=10)

        # Sound Effects Volume Control
        self.sound_label = ctk.CTkLabel(self.sidebar, text="🔊 Sound Effects", font=ctk.CTkFont(size=12, weight="bold"))
        self.sound_label.pack(pady=(20, 10), padx=10)
        
        # Call Volume Slider
        self.call_vol_label = ctk.CTkLabel(self.sidebar, text="Call Volume", font=ctk.CTkFont(size=10))
        self.call_vol_label.pack(pady=(5, 2), padx=10)
        
        self.call_vol_slider = ctk.CTkSlider(
            self.sidebar,
            from_=0,
            to=100,
            number_of_steps=20,
            command=self.on_call_volume_change,
            width=170
        )
        self.call_vol_slider.set(get_call_volume() * 100)
        self.call_vol_slider.pack(pady=(0, 10), padx=10)
        
        # Message Volume Sliders - Separate for incoming and outgoing
        self.msg_in_vol_label = ctk.CTkLabel(self.sidebar, text="📥 Received Message Volume", font=ctk.CTkFont(size=9))
        self.msg_in_vol_label.pack(pady=(5, 2), padx=10)
        
        self.msg_in_vol_slider = ctk.CTkSlider(
            self.sidebar,
            from_=0,
            to=100,
            number_of_steps=20,
            command=self.on_message_incoming_volume_change,
            width=170
        )
        self.msg_in_vol_slider.set(get_message_incoming_volume() * 100)
        self.msg_in_vol_slider.pack(pady=(0, 5), padx=10)
        
        self.msg_out_vol_label = ctk.CTkLabel(self.sidebar, text="📤 Sent Message Volume", font=ctk.CTkFont(size=9))
        self.msg_out_vol_label.pack(pady=(5, 2), padx=10)
        
        self.msg_out_vol_slider = ctk.CTkSlider(
            self.sidebar,
            from_=0,
            to=100,
            number_of_steps=20,
            command=self.on_message_outgoing_volume_change,
            width=170
        )
        self.msg_out_vol_slider.set(get_message_outgoing_volume() * 100)
        self.msg_out_vol_slider.pack(pady=(0, 10), padx=10)

        # --- CHAT AREA (RIGHT) with Tabbed Interface ---
        self.chat_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.chat_frame.grid(row=0, column=1, sticky="nsew")
        
        self.chat_frame.grid_rowconfigure(0, weight=1) # Tabs expand
        self.chat_frame.grid_columnconfigure(0, weight=1)
        
        # Tabbed Chat Interface
        self.chat_tabview = ctk.CTkTabview(self.chat_frame)
        self.chat_tabview.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        # Dictionary to store chat boxes for each contact IP
        self.chat_boxes = {}  # {ip: chat_textbox}
        self.chat_tabs = {}   # {ip: tab_name}
        
        # Create initial tab for general chat
        self.general_tab = self.chat_tabview.add("💬 General")
        self.general_chat_box = ctk.CTkTextbox(self.general_tab, state="disabled")
        self.general_chat_box.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        # Create scrollbar for general tab
        self.general_scrollbar = ctk.CTkScrollbar(self.general_tab, command=self.general_chat_box.yview)
        self.general_scrollbar.pack(side="right", fill="y", padx=5, pady=5)
        self.general_chat_box.configure(yscrollcommand=self.general_scrollbar.set)
        
        # Keep reference to currently selected tab
        self.current_chat_ip = None
        self.chat_box = self.general_chat_box  # Default to general chat

        # Message Input Area (below tabs)
        self.input_frame = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        self.input_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        self.input_frame.grid_columnconfigure(0, weight=1)
        
        # IP selection dropdown for chat
        self.chat_ip_label = ctk.CTkLabel(self.input_frame, text="Chat with:", font=ctk.CTkFont(size=10))
        self.chat_ip_label.pack(side="left", padx=(0, 5))
        
        self.chat_ip_var = ctk.StringVar(value="Select contact...")
        self.chat_ip_combo = ctk.CTkComboBox(
            self.input_frame,
            variable=self.chat_ip_var,
            values=["General"],
            state="readonly",
            command=self.on_chat_contact_selected,
            width=150
        )
        self.chat_ip_combo.pack(side="left", padx=(0, 10))
        
        # Auto-load previous chat history if available (after combo box created)
        if last_ip:
            self.create_or_switch_chat_tab(last_ip)
        
        # Message input
        self.msg_entry = ctk.CTkEntry(self.input_frame, placeholder_text="Type message...")
        self.msg_entry.pack(side="left", fill="both", expand=True, padx=(0, 10))
        self.msg_entry.bind("<Return>", self.send_msg)
        
        # Emoji toggle button
        self.emoji_btn = ctk.CTkButton(self.input_frame, text="😊", width=40, font=ctk.CTkFont(size=16), command=self.toggle_emoji_panel)
        self.emoji_btn.pack(side="left", padx=(0, 5))
        
        # Send button
        self.send_btn = ctk.CTkButton(self.input_frame, text="Send", width=60, command=self.send_msg)
        self.send_btn.pack(side="right")
        
        # Fun Sounds Panel (on right side, below chat)
        self.fun_sounds_panel_frame = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        self.fun_sounds_panel_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(5, 10))
        self.fun_sounds_panel_frame.grid_columnconfigure(0, weight=1)
        
        # Horizontal scrollable frame for sound buttons
        self.fun_sounds_frame = ctk.CTkScrollableFrame(self.fun_sounds_panel_frame, fg_color="transparent", orientation="horizontal")
        self.fun_sounds_frame.pack(fill="x", expand=True)
        
        # Load and create buttons for all fun/reaction sounds with icons
        self.fun_sound_buttons = {}
        fun_sounds = get_fun_sounds()
        if fun_sounds:
            for sound_info in fun_sounds:
                category = sound_info['path'].parent.name
                sound_name = sound_info['name']
                
                # Get icon for this sound
                icon = self._get_sound_icon(sound_name)
                
                # Create button with icon only (no text label)
                btn = ctk.CTkButton(
                    self.fun_sounds_frame,
                    text=icon,
                    width=70,
                    height=70,
                    font=ctk.CTkFont(size=32),
                    command=lambda sn=sound_name, cat=category: play_custom_sound(sn, cat)
                )
                btn.pack(side="left", padx=3, pady=5)
                self.fun_sound_buttons[sound_name] = btn
        else:
            # Show placeholder if no fun sounds found
            placeholder = ctk.CTkLabel(self.fun_sounds_frame, text="No fun sounds found", text_color="gray", font=ctk.CTkFont(size=9))
            placeholder.pack(padx=10, pady=10)

        # Emoji Panel (collapsible)
        self.emoji_panel_frame = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        self.emoji_panel_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=(5, 10))
        self.emoji_panel_frame.grid_columnconfigure(0, weight=1)
        
        # Horizontal scrollable frame for emoji buttons
        self.emoji_frame = ctk.CTkScrollableFrame(self.emoji_panel_frame, fg_color="transparent", orientation="horizontal")
        self.emoji_frame.pack(fill="x", expand=True)
        
        # Track emoji panel state
        self.emoji_panel_visible = False
        self.emoji_panel_frame.pack_forget()  # Hide initially
        
        # Create emoji buttons with better styling
        emojis = "😊😂😍🥰😎👍👎✌️🙏🤝❤️💔💛💚💙🔥⚡✨🌟💫🎉🎊🎈🎁🎀😭😡😱😴🤔😶😬😲🙈🙉🙊🤤😪😷🤒🤕😵🤮🤢🤯🤠🥴😕😟☹️🙁😞😖😢😤😠😈👿💀☠️😻😸😹😺😼😽🙀😿😾🎭"
        
        for emoji in emojis:
            emoji_btn = ctk.CTkButton(
                self.emoji_frame,
                text=emoji,
                width=50,
                height=50,
                font=ctk.CTkFont(size=24),
                fg_color="transparent",
                border_width=0,
                command=lambda e=emoji: self.insert_emoji_char(e)
            )
            emoji_btn.pack(side="left", padx=2, pady=4)

        # Start background receiver to listen for incoming calls
        self.start_background_receiver()

    def start_background_receiver(self):
        """Start a background receiver thread to listen for incoming calls."""
        try:
            if not self.background_receiver_active:
                # Reset the receiver socket to clear any stale state
                reset_receiver_socket()
                
                # Set callbacks first
                set_text_message_callback(self.receive_msg_update, self.receive_msg_update_with_sender)
                set_incoming_call_callback(self.show_incoming_call)
                set_send_custom_sound_callback(self.send_custom_sound)
                set_deafen_state(False)
                
                # Close old background stream if it exists
                if self.background_output_stream:
                    try:
                        close_stream(self.background_output_stream)
                    except Exception:
                        pass
                
                # Create a fresh output stream for the receiver
                temp_interface = get_audio_interface()
                self.background_output_stream = open_output_stream(temp_interface, self.selected_output_device_index)
                
                # Start the receive_audio loop (this will listen for both audio and text messages)
                background_thread = threading.Thread(
                    target=receive_audio,
                    args=(self.background_output_stream,),
                    daemon=True,
                    name="BackgroundReceiver"
                )
                background_thread.start()
                self.background_receiver_active = True
                print("🔊 Background receiver started (listening for calls)")
        except Exception as e:
            print(f"Error starting background receiver: {e}")
            import traceback
            traceback.print_exc()

    def populate_devices(self, cached_device_id=None):
        """Populate the device combobox with available input devices."""
        try:
            temp_interface = get_audio_interface()
            devices = get_input_devices(temp_interface)
            
            if devices:
                device_names = [f"{idx}: {name}" for idx, name in devices]
                self.device_combo.configure(values=device_names)
                
                # Select cached device if available, otherwise first device
                if cached_device_id is not None:
                    for device_name in device_names:
                        if device_name.startswith(f"{cached_device_id}:"):
                            self.device_combo.set(device_name)
                            self.selected_device_index = cached_device_id
                            break
                    else:
                        # Cached device not found, use first
                        self.device_combo.set(device_names[0])
                        self.selected_device_index = devices[0][0]
                else:
                    self.device_combo.set(device_names[0])
                    self.selected_device_index = devices[0][0]
            
            temp_interface.terminate()
        except Exception as e:
            print(f"Error populating devices: {e}")
    
    def on_device_selected(self, choice):
        """Handle device selection from combobox."""
        if choice:
            # Extract device index from the choice string (e.g., "0: Built-in Microphone")
            device_index = int(choice.split(":")[0])
            self.selected_device_index = device_index
            print(f"Selected device: {choice}")

    def populate_output_devices(self, cached_device_id=None):
        """Populate the output device combobox with available output devices."""
        try:
            temp_interface = get_audio_interface()
            devices = get_output_devices(temp_interface)
            
            if devices:
                device_names = [f"{idx}: {name}" for idx, name in devices]
                self.output_combo.configure(values=device_names)
                
                # Select cached device if available, otherwise first device
                if cached_device_id is not None:
                    for device_name in device_names:
                        if device_name.startswith(f"{cached_device_id}:"):
                            self.output_combo.set(device_name)
                            self.selected_output_device_index = cached_device_id
                            break
                    else:
                        # Cached device not found, use first
                        self.output_combo.set(device_names[0])
                        self.selected_output_device_index = devices[0][0]
                else:
                    self.output_combo.set(device_names[0])
                    self.selected_output_device_index = devices[0][0]
            
            temp_interface.terminate()
        except Exception as e:
            print(f"Error populating output devices: {e}")
    
    def on_output_device_selected(self, choice):
        """Handle output device selection from combobox."""
        if choice:
            # Extract device index from the choice string
            device_index = int(choice.split(":")[0])
            self.selected_output_device_index = device_index
            print(f"Selected output device: {choice}")

    def connect(self):
        """Initiate a voice call to the target IP."""
        target = self.ip_entry.get()
        if not target: 
            return
        
        try:
            self.target_ip = target
            self.call_state = "calling"
            
            # Initialize audio interface for this call (will use later when call is accepted)
            if not self.audio_interface:
                self.audio_interface = get_audio_interface()
            
            # Load chat history with this contact
            self.chat_box.configure(state="normal")
            history = load_history(target)
            
            from datetime import datetime
            timestamp = datetime.now().isoformat()
            time_str = format_timestamp(timestamp)
            
            if history:
                # Append call status to existing history
                self.chat_box.insert("end", f"\n[{time_str}] 📞 CALLING {target}...\n")
            else:
                self.chat_box.insert("end", f"[{time_str}] 📞 CALLING {target}...\n")
            
            self.chat_box.configure(state="disabled")
            self.chat_box.see("end")
            
            # Send call request to the target
            send_text_message("__CALL_REQUEST__", self.target_ip)
            
            # Play calling sound
            sound_calling()
            
            self.connect_btn.configure(state="disabled", text="Calling...")
            self.cancel_call_btn.configure(state="normal")
            self.ip_entry.configure(state="disabled")
            
            print(f"[CALLING] {target}...")
        except Exception as e:
            self.chat_box.configure(state="normal")
            self.chat_box.insert("end", f"Error: {str(e)}\n")
            self.chat_box.configure(state="disabled")
            print(f"Connection error: {e}")
            import traceback
            traceback.print_exc()

    def disconnect(self):
        """Disconnect from voice chat."""
        try:
            import time
            
            # Notify the other user before disconnecting
            if self.is_connected and self.target_ip:
                try:
                    send_text_message("__DISCONNECT__", self.target_ip)
                except Exception:
                    pass
            
            # Stop audio threads (only stop sender, not receiver)
            cleanup_sender()
            
            # Give sender thread time to stop
            time.sleep(0.2)
            
            # Close streams (but NOT background_output_stream)
            if self.input_stream:
                close_stream(self.input_stream)
                self.input_stream = None
            if self.output_stream and self.output_stream != self.background_output_stream:
                close_stream(self.output_stream)
            self.output_stream = None
            
            # Close audio interface
            if self.audio_interface:
                close_audio_interface(self.audio_interface)
                self.audio_interface = None
            
            # Update UI
            self.is_connected = False
            self.call_state = "idle"
            self.target_ip = None
            self.chat_box.configure(state="normal")
            from datetime import datetime
            timestamp = datetime.now().isoformat()
            time_str = format_timestamp(timestamp)
            self.chat_box.insert("end", f"[{time_str}] 📴 Disconnected\n")
            self.chat_box.configure(state="disabled")
            self.connect_btn.configure(state="normal", text="Connect Voice/Chat")
            self.disconnect_btn.configure(state="disabled")
            self.ip_entry.configure(state="normal")
            
            # Play disconnected sound
            sound_disconnected()
            
            # Restart background receiver to listen for new calls
            self.background_receiver_active = False  # Reset flag to allow restart
            self.start_background_receiver()
            
            print("✓ Disconnected from voice chat")
        except Exception as e:
            print(f"Disconnect error: {e}")
            import traceback
            traceback.print_exc()

    def show_incoming_call(self, message, caller_ip):
        """Show incoming call notification."""
        try:
            if message == "__CALL_REQUEST__":
                self.incoming_call_ip = caller_ip
                self.call_state = "ringing"
                
                # Update UI to show incoming call
                self.call_info_label.configure(text=f"From: {caller_ip}")
                self.call_frame.pack(pady=10, padx=10, fill="x")
                
                # Add to chat
                self.chat_box.configure(state="normal")
                from datetime import datetime
                timestamp = datetime.now().isoformat()
                time_str = format_timestamp(timestamp)
                self.chat_box.insert("end", f"[{time_str}] 📞 Incoming call from {caller_ip}\n")
                self.chat_box.configure(state="disabled")
                self.chat_box.see("end")
                
                # Play incoming call sound
                sound_incoming()
                
                print(f"📞 Incoming call from {caller_ip}")
        except Exception as e:
            print(f"Error showing incoming call: {e}")
            import traceback
            traceback.print_exc()

    def cancel_call(self):
        """Cancel outgoing call request."""
        try:
            if self.call_state != "calling":
                return
            
            target_ip = self.target_ip
            
            # Send cancellation message
            send_text_message("__CALL_CANCEL__", target_ip)
            
            # Reset state
            self.call_state = "idle"
            self.target_ip = None
            
            # Update UI
            self.chat_box.configure(state="normal")
            self.chat_box.insert("end", "--- Call cancelled ---\n")
            self.chat_box.configure(state="disabled")
            self.connect_btn.configure(state="normal", text="Connect Voice/Chat")
            self.cancel_call_btn.configure(state="disabled")
            self.ip_entry.configure(state="normal")
            
            print(f"✓ Call to {target_ip} cancelled")
        except Exception as e:
            print(f"Error cancelling call: {e}")
            import traceback
            traceback.print_exc()

    def accept_call(self):
        """Accept incoming call request."""
        try:
            if not self.incoming_call_ip:
                return
            
            caller_ip = self.incoming_call_ip
            self.target_ip = caller_ip
            self.call_state = "connected"
            
            # Initialize audio interface for sending audio
            self.audio_interface = get_audio_interface()
            self.input_stream = open_input_stream(self.audio_interface, self.selected_device_index)
            
            # Use the background output stream for receiving (already running)
            self.output_stream = self.background_output_stream
            
            # Save connection to cache
            save_cache(caller_ip, self.selected_device_index, self.selected_output_device_index)
            
            reset_noise_profile()
            set_deafen_state(self.is_deafened)
            
            # Start sender thread (sends microphone to caller)
            self.sender_thread = threading.Thread(
                target=send_audio,
                args=(self.input_stream, self.output_stream, self.target_ip),
                daemon=True
            )
            
            self.sender_thread.start()
            
            # Send call acceptance
            send_text_message("__CALL_ACCEPT__", self.target_ip)
            
            # Hide call notification UI
            self.call_frame.pack_forget()
            self.incoming_call_ip = None
            
            # Update UI
            self.is_connected = True
            self.chat_box.configure(state="normal")
            self.chat_box.insert("end", f"--- Call accepted with {caller_ip} ---\n")
            self.chat_box.configure(state="disabled")
            self.connect_btn.configure(state="disabled", text="Connected!")
            self.disconnect_btn.configure(state="normal")
            
            print(f"✓ Call accepted from {caller_ip}")
        except Exception as e:
            print(f"Error accepting call: {e}")
            import traceback
            traceback.print_exc()

    def reject_call(self):
        """Reject incoming call request."""
        try:
            if not self.incoming_call_ip:
                return
            
            caller_ip = self.incoming_call_ip
            
            # Send rejection
            send_text_message("__CALL_REJECT__", caller_ip)
            
            # DO NOT cleanup the receiver - it's the background receiver!
            # Just close our local output stream if we created one
            if self.output_stream:
                close_stream(self.output_stream)
                self.output_stream = None
            if self.audio_interface:
                close_audio_interface(self.audio_interface)
                self.audio_interface = None
            
            # Hide call notification UI
            self.call_frame.pack_forget()
            self.incoming_call_ip = None
            self.call_state = "idle"
            
            # Update chat
            self.chat_box.configure(state="normal")
            self.chat_box.insert("end", "--- Call rejected ---\n")
            self.chat_box.configure(state="disabled")
            
            # Restart background receiver to listen for new calls
            self.start_background_receiver()
            
            print(f"✓ Call rejected from {caller_ip}")
        except Exception as e:
            print(f"Error rejecting call: {e}")
            import traceback
            traceback.print_exc()

    def toggle_mute(self):
        self.is_muted = self.mute_btn.get()
        print(f"Muted: {self.is_muted}")

    def toggle_deafen(self):
        self.is_deafened = self.deafen_btn.get()
        set_deafen_state(self.is_deafened)
        print(f"Deafened: {self.is_deafened}")

    def on_call_volume_change(self, value):
        """Handle call volume slider change."""
        volume = float(value) / 100.0
        set_call_volume(volume)
        print(f"Call volume: {volume * 100:.0f}%")

    def on_message_incoming_volume_change(self, value):
        """Handle incoming message volume slider change."""
        volume = float(value) / 100.0
        set_message_incoming_volume(volume)
        print(f"Incoming message volume: {volume * 100:.0f}%")

    def on_message_outgoing_volume_change(self, value):
        """Handle outgoing message volume slider change."""
        volume = float(value) / 100.0
        set_message_outgoing_volume(volume)
        print(f"Outgoing message volume: {volume * 100:.0f}%")

    def create_or_switch_chat_tab(self, ip: str):
        """Create a new chat tab for an IP or switch to existing one."""
        if ip in self.chat_boxes:
            # Tab already exists, switch to it
            self.chat_tabview.set(self.chat_tabs[ip])
            self.current_chat_ip = ip
            self.chat_box = self.chat_boxes[ip]
            print(f"[OK] Switched to chat with {ip}")
        else:
            # Create new tab for this IP
            tab_name = f"💬 {ip}"
            new_tab = self.chat_tabview.add(tab_name)
            
            # Create chat textbox for this tab
            chat_box = ctk.CTkTextbox(new_tab, state="disabled")
            chat_box.pack(side="left", fill="both", expand=True, padx=5, pady=5)
            
            # Create scrollbar
            scrollbar = ctk.CTkScrollbar(new_tab, command=chat_box.yview)
            scrollbar.pack(side="right", fill="y", padx=5, pady=5)
            chat_box.configure(yscrollcommand=scrollbar.set)
            
            # Store references
            self.chat_boxes[ip] = chat_box
            self.chat_tabs[ip] = tab_name
            self.current_chat_ip = ip
            self.chat_box = chat_box
            
            # Update combo box with new contact
            current_values = list(self.chat_ip_combo.cget("values"))
            if ip not in current_values:
                current_values.append(ip)
                self.chat_ip_combo.configure(values=current_values)
            
            # Load previous history for this IP
            self.load_previous_chat(ip)
            print(f"[OK] Created new chat tab for {ip}")

    def on_chat_contact_selected(self, selected_value):
        """Handle selection from chat contact dropdown."""
        if selected_value == "General":
            # Switch to general tab
            self.chat_tabview.set("💬 General")
            self.current_chat_ip = None
            self.chat_box = self.general_chat_box
            print("[OK] Switched to general chat")
        elif selected_value and selected_value != "Select contact...":
            # Switch to specific contact tab
            self.create_or_switch_chat_tab(selected_value)

    def send_msg(self, event=None):
        msg = self.msg_entry.get()
        if not msg: return
        
        # Determine target IP - from dropdown or from active call
        if self.current_chat_ip:
            target = self.current_chat_ip
        elif self.target_ip:
            target = self.target_ip
        else:
            target = self.ip_entry.get()
        
        if not target or target == "Select contact...":
            self.chat_box.configure(state="normal")
            self.chat_box.insert("end", "[ERROR] Please select an IP first\n")
            self.chat_box.configure(state="disabled")
            return
        
        # Ensure we have a tab for this contact if not general
        if target != "General" and target not in self.chat_boxes:
            self.create_or_switch_chat_tab(target)

        # Update own UI with timestamp and date separator if needed
        from datetime import datetime
        timestamp = datetime.now().isoformat()
        
        self.chat_box.configure(state="normal")
        
        # Check if we need a date separator
        history = load_history(target)
        if history and len(history) > 0:
            last_msg = history[-1]
            prev_timestamp = last_msg.get('timestamp', '')
            if prev_timestamp and needs_date_separator(prev_timestamp, timestamp):
                date_header = format_date_header(timestamp)
                self.chat_box.insert("end", f"\n--- {date_header} ---\n")
        else:
            # First message to this contact
            date_header = format_date_header(timestamp)
            if "Chat History" not in self.chat_box.get("1.0", "end"):
                self.chat_box.insert("end", f"--- {date_header} ---\n")
        
        formatted_msg = get_formatted_message("You", msg, timestamp)
        self.chat_box.insert("end", f"{formatted_msg}\n")
        self.chat_box.configure(state="disabled")
        self.chat_box.see("end")

        # Save to history
        add_message(target, "You", msg)

        # Send to network
        send_text_message(msg, target)
        
        self.msg_entry.delete(0, "end")

    def toggle_emoji_panel(self):
        """Toggle visibility of emoji panel."""
        if self.emoji_panel_visible:
            self.emoji_panel_frame.pack_forget()
            self.emoji_panel_visible = False
        else:
            self.emoji_panel_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=(5, 10))
            self.emoji_panel_visible = True

    def insert_emoji_char(self, emoji: str):
        """Insert emoji at cursor position in message entry."""
        current_text = self.msg_entry.get()
        insert_pos = self.msg_entry.index("insert")
        new_text = current_text[:insert_pos] + emoji + current_text[insert_pos:]
        
        self.msg_entry.delete(0, "end")
        self.msg_entry.insert(0, new_text)
        
        # Set cursor after inserted emoji
        self.msg_entry.icursor(insert_pos + len(emoji))
        self.msg_entry.focus()

    def receive_msg_update(self, message):
        # This function is called when a message arrives
        self.chat_box.configure(state="normal")
        
        # Check for incoming call request
        if message == "__CALL_REQUEST__":
            # Extract IP from the message metadata (we'll handle this in receive_audio)
            # For now, we'll need to pass the IP through a different mechanism
            pass
        # Check for call acceptance
        elif message == "__CALL_ACCEPT__":
            if self.call_state == "calling":
                self.call_state = "connected"
                self.is_connected = True
                self.chat_box.insert("end", f"--- Connected to {self.target_ip} ---\n")
                self.connect_btn.configure(state="disabled", text="Connected!")
                self.disconnect_btn.configure(state="normal")
                
                # Play connected sound
                sound_connected()
                
                try:
                    # Now start sending audio since call was accepted
                    # Use the audio interface for input stream
                    if not self.audio_interface:
                        self.audio_interface = get_audio_interface()
                    
                    self.input_stream = open_input_stream(self.audio_interface, self.selected_device_index)
                    # Use background output stream for receiving audio
                    self.output_stream = self.background_output_stream
                    
                    reset_noise_profile()
                    save_cache(self.target_ip, self.selected_device_index, self.selected_output_device_index)
                    
                    self.sender_thread = threading.Thread(
                        target=send_audio,
                        args=(self.input_stream, self.output_stream, self.target_ip),
                        daemon=True
                    )
                    self.sender_thread.start()
                except Exception as e:
                    print(f"Error starting audio after call accept: {e}")
                    import traceback
                    traceback.print_exc()
        # Check for call rejection
        elif message == "__CALL_REJECT__":
            if self.call_state == "calling":
                self.call_state = "idle"
                from datetime import datetime
                timestamp = datetime.now().isoformat()
                time_str = format_timestamp(timestamp)
                self.chat_box.insert("end", f"[{time_str}] ❌ Call rejected\n")
                self.connect_btn.configure(state="normal", text="Connect Voice/Chat")
                self.cancel_call_btn.configure(state="disabled")
                self.ip_entry.configure(state="normal")
                
                # Play rejection sound
                sound_rejected()
                
                # Clean up
                cleanup_receiver()
                if self.output_stream:
                    close_stream(self.output_stream)
                    self.output_stream = None
                if self.audio_interface:
                    close_audio_interface(self.audio_interface)
                    self.audio_interface = None
        # Check for call cancellation
        elif message == "__CALL_CANCEL__":
            if self.call_state == "ringing":
                self.call_state = "idle"
                from datetime import datetime
                timestamp = datetime.now().isoformat()
                time_str = format_timestamp(timestamp)
                self.chat_box.insert("end", f"[{time_str}] ❌ Call cancelled by friend\n")
                self.call_frame.pack_forget()
                self.incoming_call_ip = None
                
                # Play cancelled sound
                sound_cancelled()
        # Check for disconnection
        elif message == "__DISCONNECT__":
            from datetime import datetime
            timestamp = datetime.now().isoformat()
            time_str = format_timestamp(timestamp)
            self.chat_box.insert("end", f"[{time_str}] 📴 Friend disconnected\n")
            
            # Play disconnected sound
            sound_disconnected()
            
            # Auto-disconnect both ways
            if self.is_connected:
                self.disconnect()
        # Regular text message
        else:
            from datetime import datetime
            timestamp = datetime.now().isoformat()
            
            # Check if we need a date separator (compare with last message if available)
            self._add_message_with_date_separator("Friend", message, timestamp)
            
            # Play message received sound
            sound_message()
            
            # Save incoming message to history
            if self.target_ip:
                add_message(self.target_ip, "Friend", message)
        
        self.chat_box.configure(state="disabled")
        self.chat_box.see("end")

    def receive_msg_update_with_sender(self, message, sender_ip):
        """Handle message with sender IP - saves even without active call."""
        # Check for custom sound message
        if message.startswith("__SOUND__") and message.endswith("__"):
            # Extract sound name and category
            # Format: __SOUND__sound_name__category__
            try:
                parts = message.split("__")
                if len(parts) >= 4:
                    sound_name = parts[2]
                    category = parts[3]
                    self.handle_custom_sound(sound_name, category, sender_ip)
                    return
            except Exception as e:
                print(f"[WARNING] Error parsing custom sound message: {e}")
                return
        
        # Check for system messages
        if message in ["__CALL_REQUEST__", "__CALL_ACCEPT__", "__CALL_REJECT__", "__CALL_CANCEL__", "__DISCONNECT__"]:
            # System messages use general chat box
            self.general_chat_box.configure(state="normal")
            # These are already handled by receive_msg_update
            self.receive_msg_update(message)
            return
        
        # Regular text message - route to sender's chat tab
        # Create/switch to chat tab for this sender
        if sender_ip not in self.chat_boxes:
            self.create_or_switch_chat_tab(sender_ip)
        
        # Get the appropriate chat box for this sender
        chat_box = self.chat_boxes[sender_ip]
        chat_box.configure(state="normal")
        
        from datetime import datetime
        timestamp = datetime.now().isoformat()
        
        # Add message with date separator if needed
        self._add_message_with_date_separator_to_box("Friend", message, timestamp, chat_box, sender_ip)
        
        # Play message received sound
        sound_message()
        
        # Always save message to history using sender IP
        add_message(sender_ip, "Friend", message)
        # Update target IP if not set (for text-only conversations)
        if not self.target_ip:
            self.target_ip = sender_ip
        
        chat_box.configure(state="disabled")
        chat_box.see("end")

    def _add_message_with_date_separator(self, sender: str, message: str, timestamp: str):
        """
        Add a message to current chat box with automatic date separator if date changed.
        
        Args:
            sender: Message sender name
            message: Message text
            timestamp: ISO timestamp string
        """
        target = self.current_chat_ip or self.target_ip
        self._add_message_with_date_separator_to_box(sender, message, timestamp, self.chat_box, target)

    def _get_sound_icon(self, sound_name: str) -> str:
        """
        Get emoji icon for a sound based on sound name.
        Returns emoji if matched, otherwise returns default speaker icon.
        
        Args:
            sound_name: Name of the sound file
            
        Returns:
            str: Emoji icon
        """
        # Sound icon mapping
        icon_map = {
            'boing': '💫',
            'squeaky': '🐭',
            'drums': '🥁',
            'cartoon-laugh': '😂',
            'crowd-laugh': '🤣',
            'sad-trombone': '🎺',
            'disappointed-trombone': '😢',
        }
        
        # Get icon from map or return default speaker icon
        return icon_map.get(sound_name, '🔊')

    def _add_message_with_date_separator_to_box(self, sender: str, message: str, timestamp: str, chat_box, contact_ip):
        """
        Add a message to a specific chat box with automatic date separator if date changed.
        
        Args:
            sender: Message sender name
            message: Message text
            timestamp: ISO timestamp string
            chat_box: The textbox to add message to
            contact_ip: The contact IP for history lookup
        """
        # Get the last message's timestamp from the chat box if available
        try:
            # Get all content from chat box to find last timestamp
            content = chat_box.get("1.0", "end")
            lines = content.strip().split("\n")
            
            # Check if we need a date separator
            need_separator = True
            if lines:
                # Look for the last actual message (skip separators and empty lines)
                for line in reversed(lines):
                    if line.strip() and not line.startswith("---"):
                        # Found a message line, extract timestamp
                        if "[" in line and "]" in line:
                            # This looks like a formatted message, but we need to check dates
                            curr_date = format_date_header(timestamp)
                            # Conservatively add separator if content exists
                            if "Chat History" not in content and "End of History" not in content:
                                # Try to find a previous message with timestamp in storage
                                if contact_ip:
                                    history = load_history(contact_ip)
                                    if history and len(history) > 0:
                                        last_msg = history[-1]
                                        prev_timestamp = last_msg.get('timestamp', '')
                                        if prev_timestamp and needs_date_separator(prev_timestamp, timestamp):
                                            need_separator = True
                                        else:
                                            need_separator = False
                        break
            
            # Add date separator if needed
            if need_separator and contact_ip:
                history = load_history(contact_ip)
                if history and len(history) > 0:
                    last_msg = history[-1]
                    prev_timestamp = last_msg.get('timestamp', '')
                    if prev_timestamp and needs_date_separator(prev_timestamp, timestamp):
                        date_header = format_date_header(timestamp)
                        chat_box.insert("end", f"\n--- {date_header} ---\n")
        except Exception:
            pass  # If anything goes wrong, just add the message
        
        # Add the message
        formatted_msg = get_formatted_message(sender, message, timestamp)
        chat_box.insert("end", f"{formatted_msg}\n")

    def load_previous_chat(self, contact_ip: str):
        """Load and display previous chat history with a contact (with date separators like WhatsApp/Discord)."""
        try:
            # Get the chat box for this contact
            if contact_ip not in self.chat_boxes:
                return
            
            chat_box = self.chat_boxes[contact_ip]
            
            history = load_history(contact_ip)
            if history:
                chat_box.configure(state="normal")
                chat_box.insert("end", f"=== Chat History with {contact_ip} ===\n")
                
                # Show last 50 messages with date separators
                messages_to_show = history[-50:]
                prev_date = None
                
                for msg in messages_to_show:
                    sender = msg.get('sender', 'Unknown')
                    text = msg.get('message', '')
                    timestamp = msg.get('timestamp', '')
                    
                    # Check if we need a date separator
                    curr_date = format_date_header(timestamp)
                    if curr_date != prev_date:
                        # Add date separator
                        chat_box.insert("end", f"\n--- {curr_date} ---\n")
                        prev_date = curr_date
                    
                    # Add the message with time only
                    formatted_msg = get_formatted_message(sender, text, timestamp)
                    chat_box.insert("end", f"{formatted_msg}\n")
                
                chat_box.insert("end", "=== End of History ===\n\n")
                chat_box.configure(state="disabled")
                self.chat_box.see("end")
        except Exception as e:
            print(f"[ERROR] Could not load previous chat: {e}")

    def start_network_scan(self):
        """Start scanning the network for available devices."""
        self.scan_btn.configure(state="disabled", text="Scanning...")
        self.device_list.configure(values=["Scanning..."], state="disabled")
        
        def on_scan_complete(devices):
            """Callback when scan completes."""
            if devices:
                formatted_devices = format_device_list(devices)
                self.device_list.configure(values=formatted_devices, state="readonly")
                self.scan_btn.configure(state="normal", text=f"Scan Network ({len(devices)} found)")
            else:
                self.device_list.configure(values=["No devices found"], state="disabled")
                self.scan_btn.configure(state="normal", text="Scan Network")
        
        # Scan network in background thread
        scan_network_async(on_scan_complete)

    def on_device_selected_from_list(self, choice):
        """Handle device selection from network list."""
        if choice and choice != "Scanning..." and choice != "No devices found":
            ip = extract_ip_from_formatted(choice)
            self.ip_entry.delete(0, "end")
            self.ip_entry.insert(0, ip)
            
            # Create or switch to chat tab for this IP
            self.create_or_switch_chat_tab(ip)
            
            # Update dropdown to show selected IP
            if ip not in self.chat_ip_combo.cget("values"):
                current_values = list(self.chat_ip_combo.cget("values"))
                current_values.append(ip)
                self.chat_ip_combo.configure(values=current_values)
            self.chat_ip_combo.set(ip)
            
            print(f"[OK] Selected device: {choice}")

    def send_custom_sound(self, sound_name: str, category: str):
        """
        Send a custom sound to the remote peer and display in chat.
        
        Args:
            sound_name: Name of the sound file (without extension)
            category: Category of the sound ('fun' or 'reactions')
        """
        try:
            # Determine target IP
            if self.current_chat_ip:
                target = self.current_chat_ip
            elif self.target_ip:
                target = self.target_ip
            else:
                print("[WARNING] No active connection to send sound")
                return
            
            # Create special message format for custom sounds
            sound_message = f"__SOUND__{sound_name}__{category}__"
            
            # Send to target
            from audio_sender import send_text_message
            send_text_message(target, sound_message)
            
            # Display in our chat that we sent it
            self.chat_box.configure(state="normal")
            
            from datetime import datetime
            timestamp = datetime.now().isoformat()
            timestamp_str = datetime.fromisoformat(timestamp).strftime("%H:%M:%S")
            
            # Get clean display name
            display_name = sound_name.replace('-', ' ').title()
            
            # Add sound notification to chat
            self.chat_box.insert("end", f"[{timestamp_str}] 🎵 You sent sound: {display_name}\n", "system")
            
            self.chat_box.configure(state="disabled")
            self.chat_box.see("end")
            
            print(f"[OK] Sent sound '{sound_name}' to {target}")
        except Exception as e:
            print(f"[ERROR] Could not send custom sound: {e}")

    def handle_custom_sound(self, sound_name: str, category: str, sender_ip: str = None):
        """
        Handle receiving and displaying a custom sound notification.
        
        Args:
            sound_name: Name of the sound that was sent
            category: Category of the sound
            sender_ip: IP of the sender (for routing to correct chat tab)
        """
        try:
            # Play the sound locally
            play_custom_sound(sound_name, category)
            
            # Get clean display name
            display_name = sound_name.replace('-', ' ').title()
            
            # Display in chat
            if sender_ip and sender_ip in self.chat_boxes:
                chat_box = self.chat_boxes[sender_ip]
            else:
                chat_box = self.chat_box
            
            chat_box.configure(state="normal")
            
            from datetime import datetime
            timestamp = datetime.now().isoformat()
            timestamp_str = datetime.fromisoformat(timestamp).strftime("%H:%M:%S")
            
            # Add sound notification to chat
            chat_box.insert("end", f"[{timestamp_str}] 🎵 Friend sent sound: {display_name}\n", "system")
            
            chat_box.configure(state="disabled")
            chat_box.see("end")
            
            print(f"[OK] Received sound: {display_name} from {sender_ip}")
        except Exception as e:
            print(f"[ERROR] Could not handle custom sound: {e}")

if __name__ == "__main__":
    app = HexChatApp()
    app.mainloop()
