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
from audio_receiver import receive_audio, cleanup_receiver, set_text_message_callback, set_deafen_state, set_incoming_call_callback, reset_receiver_socket
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
from contacts import (
    add_contact,
    get_all_contacts,
    get_contacts_display_list,
    extract_ip_from_contact_display,
    get_contact_name,
    search_contacts
)
from scan_cache import save_scan_results, load_scan_results
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
        self.incoming_call_popup = None  # Track popup window
        self.calling_popup = None  # Track calling popup window
        self.last_scan_results = []  # Store last network scan results
        self.sidebar_width = 250  # Initial sidebar width (in pixels)
        self.chat_input_height = 120  # Initial chat input height (in pixels)
        
        # Load cached values
        last_ip = get_last_connection()
        last_mic = get_last_microphone()
        last_speaker = get_last_speaker()
        
        # Set device indices from cache (will be used in settings window)
        if last_mic is not None:
            self.selected_device_index = last_mic
        if last_speaker is not None:
            self.selected_output_device_index = last_speaker
        
        # Load cached scan results from previous scan
        self.last_scan_results = load_scan_results()
        
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
        
        # Set minimum window size (can't resize smaller than this)
        self.minsize(window_width, window_height)
        
        # Set up window close handler
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # --- LAYOUT GRID ---
        self.grid_columnconfigure(0, weight=0, minsize=self.sidebar_width)  # Sidebar with dynamic width
        self.grid_columnconfigure(1, weight=0, minsize=2)  # Separator (2px)
        self.grid_columnconfigure(2, weight=1)  # Chat area expands
        self.grid_rowconfigure(0, weight=1)     # Content expands vertically

        # --- SIDEBAR (LEFT) with Scrollbar ---
        self.sidebar_frame = ctk.CTkFrame(self, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.sidebar_frame.grid_rowconfigure(0, weight=1)
        
        # Scrollable sidebar
        self.sidebar = ctk.CTkScrollableFrame(self.sidebar_frame, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        self.logo_label = ctk.CTkLabel(self.sidebar, text="HEXCHAT P2P", font=ctk.CTkFont(size=18, weight="bold"))
        self.logo_label.pack(pady=12)

        # Settings Button
        self.settings_btn = ctk.CTkButton(self.sidebar, text="⚙️ Settings", command=self.open_settings_window)
        self.settings_btn.pack(pady=5, padx=10, fill="x")

        # --- CONTACTS SECTION ---
        self.contacts_label = ctk.CTkLabel(self.sidebar, text="Saved Contacts:", font=ctk.CTkFont(size=11, weight="bold"))
        self.contacts_label.pack(pady=(10, 3), padx=10)
        
        self.contacts_combo = ctk.CTkComboBox(
            self.sidebar,
            values=get_contacts_display_list(),
            state="readonly",
            command=self.on_contact_selected
        )
        self.contacts_combo.pack(pady=(0, 5), padx=10, fill="x")
        
        # Add Contact Button
        self.add_contact_btn = ctk.CTkButton(self.sidebar, text="+ Add Contact", command=self.open_add_contact_dialog)
        self.add_contact_btn.pack(pady=5, padx=10, fill="x")

        # Connect Button
        self.connect_btn = ctk.CTkButton(self.sidebar, text="Connect Voice/Chat", command=self.connect)
        self.connect_btn.pack(pady=5, padx=10, fill="x")

        # Disconnect Button
        self.disconnect_btn = ctk.CTkButton(self.sidebar, text="Disconnect", command=self.disconnect, state="disabled")
        self.disconnect_btn.pack(pady=3, padx=10, fill="x")

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
        self.mute_btn.pack(pady=10, padx=10)
        
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
        self.chat_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.chat_frame.grid(row=0, column=2, sticky="nsew")
        
        self.chat_frame.grid_rowconfigure(0, weight=1)  # Chat tabs expand
        self.chat_frame.grid_rowconfigure(1, weight=0, minsize=2)  # Separator (2px)
        self.chat_frame.grid_rowconfigure(2, weight=0, minsize=120)  # Input frame with adjustable height
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

        # --- CHAT/INPUT SEPARATOR (DRAGGABLE) ---
        self.chat_separator = ctk.CTkFrame(self.chat_frame, height=2, fg_color="gray30")
        self.chat_separator.grid(row=1, column=0, sticky="ew", padx=10)
        self.chat_separator.bind("<Button-1>", self.on_chat_separator_drag_start)
        self.chat_separator.bind("<B1-Motion>", self.on_chat_separator_drag)
        self.chat_separator.configure(cursor="sb_v_double_arrow")  # Vertical resize cursor

        # Message Input Area (below tabs)
        self.input_frame = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        self.input_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
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
        self.fun_sounds_panel_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=(5, 10))
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

    def on_separator_drag_start(self, event):
        """Handle start of sidebar separator drag."""
        self.drag_start_x = event.x_root
        self.drag_start_width = self.sidebar_width

    def on_separator_drag(self, event):
        """Handle separator drag to resize sidebar."""
        try:
            # Calculate new width based on mouse movement
            delta = event.x_root - self.drag_start_x
            new_width = max(150, min(self.drag_start_width + delta, 600))  # Min 150px, max 600px
            
            if new_width != self.sidebar_width:
                self.sidebar_width = new_width
                # Update grid column configuration
                self.grid_columnconfigure(0, minsize=self.sidebar_width)
                self.sidebar.configure(width=self.sidebar_width)
        except Exception as e:
            print(f"Error resizing sidebar: {e}")

    def on_chat_separator_drag_start(self, event):
        """Handle start of chat/input separator drag."""
        self.chat_drag_start_y = event.y_root
        self.chat_drag_start_height = self.chat_input_height

    def on_chat_separator_drag(self, event):
        """Handle separator drag to resize chat and input areas."""
        try:
            # Calculate new height based on mouse movement
            # Negative delta when dragging up, positive when dragging down
            delta = event.y_root - self.chat_drag_start_y
            # Invert delta: dragging up should increase input area
            new_height = max(80, min(self.chat_drag_start_height - delta, 400))  # Min 80px, max 400px
            
            if new_height != self.chat_input_height:
                self.chat_input_height = new_height
                # Update input frame height
                self.chat_frame.grid_rowconfigure(2, minsize=new_height)
        except Exception as e:
            print(f"Error resizing chat area: {e}")

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
            save_cache(self.target_ip, self.selected_device_index, self.selected_output_device_index)
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
            save_cache(self.target_ip, self.selected_device_index, self.selected_output_device_index)
            print(f"Selected output device: {choice}")

    def connect(self):
        """Initiate a voice call to the target IP."""
        # Prevent multiple simultaneous calls
        if self.call_state == "calling" or self.is_connected:
            print("[!] Already in a call or connecting")
            return
        
        target = self.target_ip
        if not target:
            print("[!] No target IP selected")
            return
        
        try:
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
            
            # Show calling popup
            self.show_calling_popup(target)
            
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
            
            # Stop both audio sender and receiver threads
            cleanup_sender()
            cleanup_receiver()
            
            # Give sender/receiver threads time to stop
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
            # Keep target_ip so user can call the same person again
            # self.target_ip = None
            self.chat_box.configure(state="normal")
            from datetime import datetime
            timestamp = datetime.now().isoformat()
            time_str = format_timestamp(timestamp)
            self.chat_box.insert("end", f"[{time_str}] 📴 Disconnected\n")
            self.chat_box.configure(state="disabled")
            self.connect_btn.configure(state="normal", text="Connect Voice/Chat")
            self.disconnect_btn.configure(state="disabled")
            
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
        """Show incoming call notification as a popup dialog."""
        try:
            if message == "__CALL_REQUEST__":
                self.incoming_call_ip = caller_ip
                self.call_state = "ringing"
                
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
                
                # Show popup for incoming call
                self.show_call_popup(caller_ip)
                
                print(f"📞 Incoming call from {caller_ip}")
        except Exception as e:
            print(f"Error showing incoming call: {e}")
            import traceback
            traceback.print_exc()
    
    def show_call_popup(self, caller_ip):
        """Show incoming call as a popup dialog above chat area."""
        # Create top-level popup window
        call_popup = ctk.CTkToplevel(self)
        call_popup.title("Incoming Call")
        call_popup.geometry("350x180")
        call_popup.resizable(False, False)
        call_popup.attributes('-topmost', True)  # Keep on top
        
        # Center on screen
        call_popup.transient(self)
        
        # Store reference to close it later
        self.incoming_call_popup = call_popup
        
        # Title
        title_frame = ctk.CTkFrame(call_popup, fg_color="transparent")
        title_frame.pack(pady=20, fill="x")
        
        title_label = ctk.CTkLabel(
            title_frame,
            text="[Call] Incoming Call",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.pack()
        
        # Caller info
        info_label = ctk.CTkLabel(
            call_popup,
            text=f"From: {caller_ip}",
            font=ctk.CTkFont(size=14)
        )
        info_label.pack(pady=10)
        
        # Button frame
        button_frame = ctk.CTkFrame(call_popup, fg_color="transparent")
        button_frame.pack(pady=20, fill="x", padx=20)
        
        def on_accept():
            """Handle accept in popup."""
            call_popup.destroy()
            self.accept_call()
        
        def on_reject():
            """Handle reject in popup."""
            call_popup.destroy()
            self.reject_call()
        
        accept_btn = ctk.CTkButton(
            button_frame,
            text="Accept",
            command=on_accept,
            fg_color="green",
            hover_color="darkgreen",
            width=120
        )
        accept_btn.pack(side="left", padx=10, fill="x", expand=True)
        
        reject_btn = ctk.CTkButton(
            button_frame,
            text="Reject",
            command=on_reject,
            fg_color="red",
            hover_color="darkred",
            width=120
        )
        reject_btn.pack(side="right", padx=10, fill="x", expand=True)

    def show_calling_popup(self, target_ip):
        """Show outgoing call as a popup dialog."""
        # Create top-level popup window
        calling_popup = ctk.CTkToplevel(self)
        calling_popup.title("Calling...")
        calling_popup.geometry("350x180")
        calling_popup.resizable(False, False)
        calling_popup.attributes('-topmost', True)  # Keep on top
        
        # Center on screen
        calling_popup.transient(self)
        
        # Store reference to close it later
        self.calling_popup = calling_popup
        
        # Title
        title_frame = ctk.CTkFrame(calling_popup, fg_color="transparent")
        title_frame.pack(pady=20, fill="x")
        
        title_label = ctk.CTkLabel(
            title_frame,
            text="[Calling...]",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.pack()
        
        # Target info
        info_label = ctk.CTkLabel(
            calling_popup,
            text=f"To: {target_ip}",
            font=ctk.CTkFont(size=14)
        )
        info_label.pack(pady=10)
        
        # Button frame
        button_frame = ctk.CTkFrame(calling_popup, fg_color="transparent")
        button_frame.pack(pady=20, fill="x", padx=20)
        
        def on_cancel():
            """Handle cancel in popup."""
            calling_popup.destroy()
            self.cancel_call()
        
        cancel_btn = ctk.CTkButton(
            button_frame,
            text="Cancel Call",
            command=on_cancel,
            fg_color="red",
            hover_color="darkred",
            width=200
        )
        cancel_btn.pack(padx=10, fill="x", expand=True)

    def cancel_call(self):
        """Cancel outgoing call request."""
        try:
            if self.call_state != "calling":
                return
            
            target_ip = self.target_ip
            
            # Send cancellation message
            try:
                send_text_message("__CALL_CANCEL__", target_ip)
            except Exception:
                pass
            
            # Clean up any audio threads that might have been started
            try:
                cleanup_sender()
            except Exception:
                pass
            
            try:
                cleanup_receiver()
            except Exception:
                pass
            
            # Close streams
            try:
                if self.input_stream:
                    close_stream(self.input_stream)
                    self.input_stream = None
            except Exception:
                pass
            
            try:
                if self.output_stream and self.output_stream != self.background_output_stream:
                    close_stream(self.output_stream)
                self.output_stream = None
            except Exception:
                pass
            
            # Close audio interface
            try:
                if self.audio_interface:
                    close_audio_interface(self.audio_interface)
                    self.audio_interface = None
            except Exception:
                pass
            
            # Close popup if open
            if self.calling_popup:
                try:
                    self.calling_popup.destroy()
                except:
                    pass
                self.calling_popup = None
            
            # Reset state FIRST (keep target_ip so user can call again without reselecting)
            self.call_state = "idle"
            self.is_connected = False
            
            # Update UI - ensure button is fully enabled
            try:
                self.chat_box.configure(state="normal")
                self.chat_box.insert("end", "--- Call cancelled ---\n")
                self.chat_box.configure(state="disabled")
            except Exception:
                pass
            
            # CRITICAL: Make sure connect button is enabled
            self.connect_btn.configure(state="normal", text="Connect Voice/Chat")
            
            # Restart background receiver LAST to listen for new calls
            try:
                self.background_receiver_active = False  # Reset flag to allow restart
                self.start_background_receiver()
            except Exception as e:
                print(f"Warning: Could not restart background receiver: {e}")
            
            print(f"✓ Call to {target_ip} cancelled - Ready to call again")
        except Exception as e:
            print(f"Error cancelling call: {e}")
            import traceback
            traceback.print_exc()
            # FORCE enable the button if something went wrong
            self.connect_btn.configure(state="normal", text="Connect Voice/Chat")
            self.call_state = "idle"

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
            
            # Close popup if open
            if self.incoming_call_popup:
                try:
                    self.incoming_call_popup.destroy()
                except:
                    pass
                self.incoming_call_popup = None
            
            # Hide call notification UI (old sidebar frame)
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
            
            # Close popup if open
            if self.incoming_call_popup:
                try:
                    self.incoming_call_popup.destroy()
                except:
                    pass
                self.incoming_call_popup = None
            
            # DO NOT cleanup the receiver - it's the background receiver!
            # Just close our local output stream if we created one
            if self.output_stream:
                close_stream(self.output_stream)
                self.output_stream = None
            if self.audio_interface:
                close_audio_interface(self.audio_interface)
                self.audio_interface = None
            
            # Hide call notification UI (old sidebar frame)
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
            target = None
        
        if not target:
            self.chat_box.configure(state="normal")
            self.chat_box.insert("end", "[ERROR] Please select a contact first\n")
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
                
                # Close calling popup if open
                if self.calling_popup:
                    try:
                        self.calling_popup.destroy()
                    except:
                        pass
                    self.calling_popup = None
                
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

    def on_contact_selected(self, choice):
        """Handle contact selection from dropdown."""
        if choice and " - " in choice:
            ip = extract_ip_from_contact_display(choice)
            if ip:
                self.target_ip = ip
                
                # Load chat history for this contact
                self.chat_box.configure(state="normal")
                self.chat_box.delete("1.0", "end")
                
                history = load_history(ip)
                if history:
                    self.chat_box.insert("end", f"=== Chat History with {choice} ===\n")
                    for msg in history:
                        sender = msg.get('sender', 'Unknown')
                        text = msg.get('message', '')
                        timestamp = msg.get('timestamp', '')
                        formatted_msg = get_formatted_message(sender, text, timestamp)
                        self.chat_box.insert("end", f"{formatted_msg}\n")
                    self.chat_box.insert("end", "=== End of History ===\n\n")
                else:
                    self.chat_box.insert("end", f"[New chat with {choice}]\n\n")
                
                self.chat_box.configure(state="disabled")
                self.chat_box.see("end")
                
                print(f"[OK] Selected contact: {choice}")

    def open_settings_window(self):
        """Open settings window for microphone and speaker configuration."""
        try:
            # Create settings window
            settings_window = ctk.CTkToplevel(self)
            settings_window.title("Settings")
            settings_window.geometry("450x350")
            settings_window.resizable(False, False)
            settings_window.transient(self)
            
            # Title
            title_label = ctk.CTkLabel(
                settings_window,
                text="Audio Settings",
                font=ctk.CTkFont(size=16, weight="bold")
            )
            title_label.pack(pady=15, padx=20)
            
            # Get audio interface for device enumeration
            temp_interface = get_audio_interface()
            
            # Microphone Section
            mic_frame = ctk.CTkFrame(settings_window)
            mic_frame.pack(pady=10, padx=20, fill="x")
            
            mic_label = ctk.CTkLabel(mic_frame, text="Microphone:", font=ctk.CTkFont(size=12, weight="bold"))
            mic_label.pack(anchor="w", pady=(0, 5))
            
            mic_combo = ctk.CTkComboBox(
                mic_frame,
                values=[],
                state="readonly"
            )
            mic_combo.pack(fill="x")
            
            # Populate microphone list
            devices = get_input_devices(temp_interface)
            selected_mic_idx = None
            if devices:
                device_names = [f"{idx}: {name}" for idx, name in devices]
                mic_combo.configure(values=device_names)
                # Set to cached device
                for idx, name in devices:
                    if idx == self.selected_device_index:
                        mic_combo.set(f"{idx}: {name}")
                        selected_mic_idx = idx
                        break
                if not mic_combo.get():  # If not set, use first
                    mic_combo.set(device_names[0])
                    selected_mic_idx = devices[0][0]
            
            # Speaker Section
            speaker_frame = ctk.CTkFrame(settings_window)
            speaker_frame.pack(pady=10, padx=20, fill="x")
            
            speaker_label = ctk.CTkLabel(speaker_frame, text="Speaker:", font=ctk.CTkFont(size=12, weight="bold"))
            speaker_label.pack(anchor="w", pady=(0, 5))
            
            speaker_combo = ctk.CTkComboBox(
                speaker_frame,
                values=[],
                state="readonly"
            )
            speaker_combo.pack(fill="x")
            
            # Populate speaker list
            output_devices = get_output_devices(temp_interface)
            selected_speaker_idx = None
            if output_devices:
                device_names = [f"{idx}: {name}" for idx, name in output_devices]
                speaker_combo.configure(values=device_names)
                # Set to cached device
                for idx, name in output_devices:
                    if idx == self.selected_output_device_index:
                        speaker_combo.set(f"{idx}: {name}")
                        selected_speaker_idx = idx
                        break
                if not speaker_combo.get():  # If not set, use first
                    speaker_combo.set(device_names[0])
                    selected_speaker_idx = output_devices[0][0]
            
            # Button Frame
            button_frame = ctk.CTkFrame(settings_window, fg_color="transparent")
            button_frame.pack(pady=20, padx=20, fill="x")
            
            def save_settings():
                """Save selected audio settings."""
                try:
                    # Extract device indices
                    if mic_combo.get():
                        mic_idx = int(mic_combo.get().split(":")[0])
                        self.selected_device_index = mic_idx
                    
                    if speaker_combo.get():
                        speaker_idx = int(speaker_combo.get().split(":")[0])
                        self.selected_output_device_index = speaker_idx
                    
                    # Save to cache
                    save_cache(self.target_ip, self.selected_device_index, self.selected_output_device_index)
                    
                    print(f"✓ Settings saved - Mic: {self.selected_device_index}, Speaker: {self.selected_output_device_index}")
                    settings_window.destroy()
                except Exception as e:
                    print(f"Error saving settings: {e}")
            
            # Save Button
            save_btn = ctk.CTkButton(button_frame, text="Save", command=save_settings, fg_color="green", hover_color="darkgreen")
            save_btn.pack(side="left", padx=5, fill="x", expand=True)
            
            # Close Button
            close_btn = ctk.CTkButton(button_frame, text="Cancel", command=settings_window.destroy)
            close_btn.pack(side="right", padx=5, fill="x", expand=True)
            
            # Clean up temp interface
            temp_interface.terminate()
            
            print("✓ Settings window opened")
        except Exception as e:
            print(f"Error opening settings window: {e}")
            import traceback
            traceback.print_exc()

    def open_add_contact_dialog(self):
        """Open dialog to add a new contact with network scan integration."""
        # Create top-level dialog window
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add Contact")
        dialog.geometry("450x620")
        dialog.resizable(False, False)
        
        # Center the dialog
        dialog.transient(self)
        dialog.grab_set()
        
        # Title
        title_label = ctk.CTkLabel(
            dialog,
            text="Add New Contact",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=15)
        
        # --- IP Entry Section ---
        ip_label = ctk.CTkLabel(dialog, text="IP Address:", font=ctk.CTkFont(size=12, weight="bold"))
        ip_label.pack(pady=(10, 5), padx=20, anchor="w")
        
        ip_entry = ctk.CTkEntry(dialog, placeholder_text="Manually enter IP or scan below")
        ip_entry.pack(pady=(0, 10), padx=20, fill="x")
        
        # --- Network Scan Section ---
        scan_label = ctk.CTkLabel(dialog, text="Or scan for devices:", font=ctk.CTkFont(size=12, weight="bold"))
        scan_label.pack(pady=(10, 5), padx=20, anchor="w")
        
        # Scan button
        def perform_scan():
            """Scan network and populate device list."""
            scan_btn.configure(state="disabled", text="Scanning...")
            device_combo.configure(values=["Scanning..."], state="disabled")
            
            def on_scan_complete(devices):
                """Callback when scan completes."""
                if devices:
                    formatted_devices = format_device_list(devices)
                    self.last_scan_results = formatted_devices  # Store results
                    save_scan_results(formatted_devices)  # Persist to disk
                    device_combo.configure(values=formatted_devices, state="readonly")
                    scan_btn.configure(state="normal", text=f"Scan Again ({len(devices)} found)")
                else:
                    device_combo.configure(values=["No devices found"], state="disabled")
                    scan_btn.configure(state="normal", text="Scan Again")
            
            # Scan network in background thread
            scan_network_async(on_scan_complete)
        
        scan_btn = ctk.CTkButton(dialog, text="Scan Network", command=perform_scan)
        scan_btn.pack(pady=5, padx=20, fill="x")
        
        # Device list dropdown - pre-populate with last scan results if available
        initial_values = self.last_scan_results if self.last_scan_results else []
        device_combo_state = "readonly" if self.last_scan_results else "disabled"
        
        device_combo = ctk.CTkComboBox(
            dialog,
            values=initial_values,
            state=device_combo_state,
            command=lambda choice: ip_entry.delete(0, "end") or ip_entry.insert(0, extract_ip_from_formatted(choice)) if (choice and choice not in ["Scanning...", "No devices found"]) else None
        )
        device_combo.pack(pady=(0, 10), padx=20, fill="x")
        
        # --- Name Entry Section ---
        name_label = ctk.CTkLabel(dialog, text="Contact Name (optional):", font=ctk.CTkFont(size=12, weight="bold"))
        name_label.pack(pady=(15, 5), padx=20, anchor="w")
        
        name_entry = ctk.CTkEntry(dialog, placeholder_text="Leave blank for 'piggy'")
        name_entry.pack(pady=(0, 10), padx=20, fill="x")
        
        # Info label
        info_frame = ctk.CTkFrame(dialog, fg_color="gray30", corner_radius=5)
        info_frame.pack(pady=15, padx=20, fill="x")
        
        info_label = ctk.CTkLabel(
            info_frame,
            text="How to add:\n1. Manually enter an IP, or\n2. Click 'Scan Network' to find nearby devices\n3. Select from results to auto-fill IP\n4. Enter a name or leave blank for 'piggy'\n5. Click 'OK'",
            font=ctk.CTkFont(size=10),
            text_color="lightgray",
            justify="left"
        )
        info_label.pack(pady=10, padx=10)
        
        # Button frame
        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(pady=15, padx=20, fill="x")
        
        def save_contact():
            """Save the contact and close dialog."""
            ip = ip_entry.get().strip()
            name = name_entry.get().strip()
            
            if not ip:
                # Show error
                ip_entry.configure(border_color="red")
                return
            
            # Reset border color to default
            ip_entry.configure(border_color="gray")
            
            # Use default name if not provided
            if not name:
                name = "piggy"
            
            # Add contact
            if add_contact(ip, name):
                # Update contacts dropdown
                self.refresh_contacts_dropdown()
                self.contacts_combo.set(f"{name} - {ip}")
                self.target_ip = ip
                dialog.destroy()
            else:
                ip_entry.configure(border_color="red")
        
        save_btn = ctk.CTkButton(button_frame, text="OK", command=save_contact, fg_color="green", hover_color="darkgreen")
        save_btn.pack(side="left", padx=5, fill="x", expand=True)
        
        cancel_btn = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=dialog.destroy,
            fg_color="gray60",
            hover_color="gray50"
        )
        cancel_btn.pack(side="right", padx=5, fill="x", expand=True)
    
    def refresh_contacts_dropdown(self):
        """Refresh the contacts dropdown list."""
        try:
            contacts_list = get_contacts_display_list()
            self.contacts_combo.configure(values=contacts_list)
            if contacts_list:
                # Try to keep current selection if it still exists
                current = self.contacts_combo.get()
                if current not in contacts_list:
                    self.contacts_combo.set("")
        except Exception as e:
            print(f"Error refreshing contacts: {e}")
    
    def on_closing(self):
        """Handle window close event - disconnect from call and clean up."""
        try:
            # Cancel outgoing call if in calling state
            if self.call_state == "calling":
                self.cancel_call()
            
            # Disconnect if currently connected
            if self.is_connected:
                self.disconnect()
            
            # Close any open popups
            if self.incoming_call_popup:
                try:
                    self.incoming_call_popup.destroy()
                except:
                    pass
            
            if self.calling_popup:
                try:
                    self.calling_popup.destroy()
                except:
                    pass
            
            # Clean up background receiver
            cleanup_receiver()
            
            # Destroy the main window
            self.destroy()
        except Exception as e:
            print(f"Error during window close: {e}")
            # Force close if cleanup fails
            self.destroy()

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
            send_text_message(sound_message, target)
            
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
