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
        
        # Window Setup
        self.title("HexChat")
        self.geometry("800x600")

        # --- LAYOUT GRID ---
        self.grid_columnconfigure(0, weight=0)  # Sidebar fixed width
        self.grid_columnconfigure(1, weight=1)  # Chat area expands
        self.grid_rowconfigure(0, weight=1)     # Content expands vertically

        # --- SIDEBAR (LEFT) ---
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)  # Keep sidebar at fixed width

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

        # --- CHAT AREA (RIGHT) ---
        self.chat_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.chat_frame.grid(row=0, column=1, sticky="nsew")
        
        self.chat_frame.grid_rowconfigure(0, weight=1) # History expands
        self.chat_frame.grid_columnconfigure(0, weight=1)

        # Chat History box
        self.chat_box = ctk.CTkTextbox(self.chat_frame, state="disabled")
        self.chat_box.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

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

    def start_background_receiver(self):
        """Start a background receiver thread to listen for incoming calls."""
        try:
            if not self.background_receiver_active:
                # Reset the receiver socket to clear any stale state
                reset_receiver_socket()
                
                # Set callbacks first
                set_text_message_callback(self.receive_msg_update)
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
        target = self.ip_entry.get()
        if not target: 
            return
        
        try:
            self.target_ip = target
            self.call_state = "calling"
            
            # Initialize audio interface for this call (will use later when call is accepted)
            if not self.audio_interface:
                self.audio_interface = get_audio_interface()
            
            # Send call request to the target
            send_text_message("__CALL_REQUEST__", self.target_ip)
            
            self.chat_box.configure(state="normal")
            self.chat_box.insert("end", f"📞 Calling {target}...\n")
            self.chat_box.configure(state="disabled")
            self.connect_btn.configure(state="disabled", text="Calling...")
            self.ip_entry.configure(state="disabled")
            
            print(f"📞 Calling {target}...")
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
            self.chat_box.insert("end", "--- Disconnected ---\n")
            self.chat_box.configure(state="disabled")
            self.connect_btn.configure(state="normal", text="Connect Voice/Chat")
            self.disconnect_btn.configure(state="disabled")
            self.ip_entry.configure(state="normal")
            
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
                self.chat_box.insert("end", f"📞 Incoming call from {caller_ip}\n")
                self.chat_box.configure(state="disabled")
                self.chat_box.see("end")
                
                print(f"📞 Incoming call from {caller_ip}")
        except Exception as e:
            print(f"Error showing incoming call: {e}")
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

    def send_msg(self, event=None):
        msg = self.msg_entry.get()
        if not msg: return

        # Update own UI
        self.chat_box.configure(state="normal")
        self.chat_box.insert("end", f"You: {msg}\n")
        self.chat_box.configure(state="disabled")
        self.chat_box.see("end")

        # Send to network
        if self.is_connected and self.target_ip:
            send_text_message(msg, self.target_ip)
        
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
                self.ip_entry.configure(state="normal")
                
                # Clean up
                cleanup_receiver()
                if self.output_stream:
                    close_stream(self.output_stream)
                    self.output_stream = None
                if self.audio_interface:
                    close_audio_interface(self.audio_interface)
                    self.audio_interface = None
        # Check for disconnection
        elif message == "__DISCONNECT__":
            self.chat_box.insert("end", "--- Friend disconnected ---\n")
            # Auto-disconnect both ways
            if self.is_connected:
                self.disconnect()
        # Regular text message
        else:
            self.chat_box.insert("end", f"Friend: {message}\n")
        
        self.chat_box.configure(state="disabled")
        self.chat_box.see("end")

if __name__ == "__main__":
    app = HexChatApp()
    app.mainloop()
