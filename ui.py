# ui.py
import customtkinter as ctk
import threading
from audio_io import (
    get_audio_interface,
    get_input_devices,
    open_input_stream,
    open_output_stream,
    close_stream,
    close_audio_interface
)
from audio_sender import send_audio, cleanup_sender, send_text_message
from audio_receiver import receive_audio, cleanup_receiver, set_text_message_callback
from audio_filter import reset_noise_profile
from connection_cache import (
    get_last_connection,
    get_last_microphone,
    has_cached_connection,
    save_cache,
)


# --- APPEARANCE ---
ctk.set_appearance_mode("Dark")  # Modes: "System", "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue", "green", "dark-blue"


class DiscordApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.audio_interface = None
        self.input_stream = None
        self.output_stream = None
        self.target_ip = None
        self.is_muted = False
        self.is_deafened = False
        self.receiver_thread = None
        self.sender_thread = None
        self.is_connected = False
        self.selected_device_index = 0
        
        # Load cached values
        last_ip = get_last_connection()
        last_mic = get_last_microphone()
        
        # Window Setup
        self.title("Local Discord")
        self.geometry("800x600")

        # --- LAYOUT GRID ---
        self.grid_columnconfigure(0, weight=0)  # Sidebar fixed width
        self.grid_columnconfigure(1, weight=1)  # Chat area expands
        self.grid_rowconfigure(0, weight=1)     # Content expands vertically

        # --- SIDEBAR (LEFT) ---
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)  # Keep sidebar at fixed width

        self.logo_label = ctk.CTkLabel(self.sidebar, text="DISCORD P2P", font=ctk.CTkFont(size=20, weight="bold"))
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

        # IP Input with cached value
        self.ip_entry = ctk.CTkEntry(self.sidebar, placeholder_text="Enter Friend's IP")
        if last_ip:
            self.ip_entry.insert(0, last_ip)
        self.ip_entry.pack(pady=10, padx=10)

        # Connect Button
        self.connect_btn = ctk.CTkButton(self.sidebar, text="Connect Voice/Chat", command=self.connect)
        self.connect_btn.pack(pady=10, padx=10, fill="x")

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

    def connect(self):
        target = self.ip_entry.get()
        if not target: 
            return
        
        try:
            self.target_ip = target
            self.audio_interface = get_audio_interface()
            self.input_stream = open_input_stream(self.audio_interface, self.selected_device_index)
            self.output_stream = open_output_stream(self.audio_interface)
            
            # Save connection to cache
            save_cache(target, self.selected_device_index)
            
            reset_noise_profile()
            
            # Set up text message callback
            set_text_message_callback(self.receive_msg_update)
            
            # Start receiver thread (listens for incoming audio)
            self.receiver_thread = threading.Thread(
                target=receive_audio,
                args=(self.output_stream,),
                daemon=True
            )
            
            # Start sender thread (sends microphone to target)
            self.sender_thread = threading.Thread(
                target=send_audio,
                args=(self.input_stream, self.output_stream, self.target_ip),
                daemon=True
            )
            
            self.receiver_thread.start()
            self.sender_thread.start()
            
            self.is_connected = True
            self.chat_box.configure(state="normal")
            self.chat_box.insert("end", f"--- Connected to {target} ---\n")
            self.chat_box.configure(state="disabled")
            self.connect_btn.configure(state="disabled", text="Connected!")
            self.ip_entry.configure(state="disabled")
        except Exception as e:
            self.chat_box.configure(state="normal")
            self.chat_box.insert("end", f"Error: {str(e)}\n")
            self.chat_box.configure(state="disabled")
            print(f"Connection error: {e}")
            import traceback
            traceback.print_exc()

    def toggle_mute(self):
        self.is_muted = self.mute_btn.get()
        print(f"Muted: {self.is_muted}")

    def toggle_deafen(self):
        self.is_deafened = self.deafen_btn.get()
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
        self.chat_box.insert("end", f"Friend: {message}\n")
        self.chat_box.configure(state="disabled")
        self.chat_box.see("end")

if __name__ == "__main__":
    app = DiscordApp()
    app.mainloop()
