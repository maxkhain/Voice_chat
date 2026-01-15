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
from chat_history import add_message, load_history, display_history, clear_history, get_formatted_message, format_timestamp
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
        
        # Load cached values
        last_ip = get_last_connection()
        last_mic = get_last_microphone()
        last_speaker = get_last_speaker()
        
        # Load cached scan results from previous scan
        self.last_scan_results = load_scan_results()
        
        # Populate devices from cache (for later use in settings)
        self.populate_devices(last_mic)
        self.populate_output_devices(last_speaker)
        
        # Store last IP for later use
        self.last_loaded_ip = last_ip
        
        # Window Setup
        self.title("HexChat")
        self.geometry("800x600")
        
        # Set up window close handler
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # --- LAYOUT GRID ---
        self.grid_columnconfigure(0, weight=0, minsize=self.sidebar_width)  # Sidebar with dynamic width
        self.grid_columnconfigure(1, weight=0, minsize=2)  # Separator (2px)
        self.grid_columnconfigure(2, weight=1)  # Chat area expands
        self.grid_rowconfigure(0, weight=1)     # Content expands vertically

        # --- SIDEBAR (LEFT) ---
        self.sidebar = ctk.CTkFrame(self, width=self.sidebar_width, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)  # Keep sidebar at fixed width

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
        self.mute_btn.pack(pady=10, padx=10)
        
        self.deafen_btn = ctk.CTkSwitch(self.sidebar, text="Deafen Audio", command=self.toggle_deafen)
        self.deafen_btn.pack(pady=5, padx=10)

        # --- SEPARATOR (DRAGGABLE) ---
        self.separator = ctk.CTkFrame(self, width=2, fg_color="gray30")
        self.separator.grid(row=0, column=1, sticky="nsew")
        self.separator.bind("<Button-1>", self.on_separator_drag_start)
        self.separator.bind("<B1-Motion>", self.on_separator_drag)
        self.separator.configure(cursor="sb_h_double_arrow")  # Horizontal resize cursor
        
        # --- CHAT AREA (RIGHT) ---
        self.chat_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.chat_frame.grid(row=0, column=2, sticky="nsew")
        
        self.chat_frame.grid_rowconfigure(0, weight=1) # History expands
        self.chat_frame.grid_columnconfigure(0, weight=1)

        # Chat History box
        self.chat_box = ctk.CTkTextbox(self.chat_frame, state="disabled")
        self.chat_box.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        # Auto-load previous chat history if available
        if last_ip:
            self.load_previous_chat(last_ip)

        # Message Input
        self.entry_frame = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        self.entry_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        self.entry_frame.grid_columnconfigure(0, weight=1)
        
        self.msg_entry = ctk.CTkEntry(self.entry_frame, placeholder_text="Message @Friend")
        self.msg_entry.pack(side="left", fill="both", expand=True, padx=(0, 10))
        self.msg_entry.bind("<Return>", self.send_msg) # Send on Enter key
        self.send_btn = ctk.CTkButton(self.entry_frame, text="Send", width=60, command=self.send_msg)
        self.send_btn.pack(side="right")

        # Start background receiver to listen for incoming calls
        self.start_background_receiver()

    def on_separator_drag_start(self, event):
        """Handle start of separator drag."""
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

    def start_background_receiver(self):
        """Start a background receiver thread to listen for incoming calls."""
        try:
            if not self.background_receiver_active:
                # Reset the receiver socket to clear any stale state
                reset_receiver_socket()
                
                # Set callbacks first
                set_text_message_callback(self.receive_msg_update, self.receive_msg_update_with_sender)
                set_incoming_call_callback(self.show_incoming_call)
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
            if history:
                # Append call status to existing history
                self.chat_box.insert("end", f"\n[CALLING] {target}...\n")
            else:
                self.chat_box.insert("end", f"[CALLING] {target}...\n")
            
            self.chat_box.configure(state="disabled")
            self.chat_box.see("end")
            
            # Send call request to the target
            send_text_message("__CALL_REQUEST__", self.target_ip)
            
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
            self.chat_box.insert("end", "--- Disconnected ---\n")
            self.chat_box.configure(state="disabled")
            self.connect_btn.configure(state="normal", text="Connect Voice/Chat")
            self.disconnect_btn.configure(state="disabled")
            
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
                self.chat_box.insert("end", f"[Call] Incoming call from {caller_ip}\n")
                self.chat_box.configure(state="disabled")
                self.chat_box.see("end")
                
                # Create popup dialog for incoming call
                self.show_call_popup(caller_ip)
                
                print(f"[Call] Incoming call from {caller_ip}")
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
            self.cancel_call_btn.configure(state="disabled")
            
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

    def send_msg(self, event=None):
        msg = self.msg_entry.get()
        if not msg: return
        
        # Check if we have a target IP
        target = self.target_ip
        if not target:
            self.chat_box.configure(state="normal")
            self.chat_box.insert("end", "[ERROR] Please select a contact first\n")
            self.chat_box.configure(state="disabled")
            return

        # Update own UI with timestamp
        from datetime import datetime
        timestamp = datetime.now().isoformat()
        formatted_msg = get_formatted_message("You", msg, timestamp)
        
        self.chat_box.configure(state="normal")
        self.chat_box.insert("end", f"{formatted_msg}\n")
        self.chat_box.configure(state="disabled")
        self.chat_box.see("end")

        # Save to history
        add_message(target, "You", msg)

        # Send to network
        send_text_message(msg, target)
        
        self.msg_entry.delete(0, "end")

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
                self.chat_box.insert("end", "--- Call rejected ---\n")
                self.connect_btn.configure(state="normal", text="Connect Voice/Chat")
                self.cancel_call_btn.configure(state="disabled")
                self.ip_entry.configure(state="normal")
                
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
                self.chat_box.insert("end", "--- Call cancelled by friend ---\n")
                self.call_frame.pack_forget()
                self.incoming_call_ip = None
        # Check for disconnection
        elif message == "__DISCONNECT__":
            self.chat_box.insert("end", "--- Friend disconnected ---\n")
            # Auto-disconnect both ways
            if self.is_connected:
                self.disconnect()
        # Regular text message
        else:
            from datetime import datetime
            timestamp = datetime.now().isoformat()
            formatted_msg = get_formatted_message("Friend", message, timestamp)
            self.chat_box.insert("end", f"{formatted_msg}\n")
            # Save incoming message to history
            if self.target_ip:
                add_message(self.target_ip, "Friend", message)
        
        self.chat_box.configure(state="disabled")
        self.chat_box.see("end")

    def receive_msg_update_with_sender(self, message, sender_ip):
        """Handle message with sender IP - saves even without active call."""
        self.chat_box.configure(state="normal")
        
        # Check for incoming call request
        if message == "__CALL_REQUEST__":
            # Call request with sender IP - handled by callback
            pass
        # Check for system messages
        elif message in ["__CALL_ACCEPT__", "__CALL_REJECT__", "__CALL_CANCEL__", "__DISCONNECT__"]:
            # These are already handled by receive_msg_update
            self.receive_msg_update(message)
            return
        # Regular text message - save regardless of connection state
        else:
            from datetime import datetime
            timestamp = datetime.now().isoformat()
            formatted_msg = get_formatted_message("Friend", message, timestamp)
            self.chat_box.insert("end", f"{formatted_msg}\n")
            # Always save message to history using sender IP
            add_message(sender_ip, "Friend", message)
            # Update target IP if not set (for text-only conversations)
            if not self.target_ip:
                self.target_ip = sender_ip
        
        self.chat_box.configure(state="disabled")
        self.chat_box.see("end")

    def load_previous_chat(self, contact_ip: str):
        """Load and display previous chat history with a contact."""
        try:
            history = load_history(contact_ip)
            if history:
                self.chat_box.configure(state="normal")
                self.chat_box.insert("end", f"=== Chat History with {contact_ip} ===\n")
                
                # Show last 50 messages with timestamps
                for msg in history[-50:]:
                    sender = msg.get('sender', 'Unknown')
                    text = msg.get('message', '')
                    timestamp = msg.get('timestamp', '')
                    formatted_msg = get_formatted_message(sender, text, timestamp)
                    self.chat_box.insert("end", f"{formatted_msg}\n")
                
                self.chat_box.insert("end", "=== End of History ===\n\n")
                self.chat_box.configure(state="disabled")
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
            settings_window.geometry("450x300")
            settings_window.resizable(False, False)
            settings_window.transient(self)
            
            # Title
            title_label = ctk.CTkLabel(
                settings_window,
                text="Audio Settings",
                font=ctk.CTkFont(size=16, weight="bold")
            )
            title_label.pack(pady=15, padx=20)
            
            # Microphone Section
            mic_frame = ctk.CTkFrame(settings_window)
            mic_frame.pack(pady=10, padx=20, fill="x")
            
            mic_label = ctk.CTkLabel(mic_frame, text="Microphone:", font=ctk.CTkFont(size=12, weight="bold"))
            mic_label.pack(anchor="w", pady=(0, 5))
            
            mic_combo = ctk.CTkComboBox(
                mic_frame,
                values=[],
                state="readonly",
                command=self.on_device_selected
            )
            mic_combo.pack(fill="x")
            
            # Populate microphone list
            devices = get_input_devices()
            if devices:
                device_names = [f"{idx}: {name}" for idx, name in devices]
                mic_combo.configure(values=device_names)
                # Set to cached device
                for idx, name in devices:
                    if idx == self.selected_device_index:
                        mic_combo.set(f"{idx}: {name}")
                        break
            
            # Speaker Section
            speaker_frame = ctk.CTkFrame(settings_window)
            speaker_frame.pack(pady=10, padx=20, fill="x")
            
            speaker_label = ctk.CTkLabel(speaker_frame, text="Speaker:", font=ctk.CTkFont(size=12, weight="bold"))
            speaker_label.pack(anchor="w", pady=(0, 5))
            
            speaker_combo = ctk.CTkComboBox(
                speaker_frame,
                values=[],
                state="readonly",
                command=self.on_output_device_selected
            )
            speaker_combo.pack(fill="x")
            
            # Populate speaker list
            output_devices = get_output_devices()
            if output_devices:
                device_names = [f"{idx}: {name}" for idx, name in output_devices]
                speaker_combo.configure(values=device_names)
                # Set to cached device
                for idx, name in output_devices:
                    if idx == self.selected_output_device_index:
                        speaker_combo.set(f"{idx}: {name}")
                        break
            
            # Close Button
            close_btn = ctk.CTkButton(settings_window, text="Close", command=settings_window.destroy)
            close_btn.pack(pady=20, padx=20, fill="x")
            
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

if __name__ == "__main__":
    app = HexChatApp()
    app.mainloop()
