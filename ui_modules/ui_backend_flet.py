# ui_backend_flet.py
"""
Backend logic integration for Flet UI
Connects UI events to audio modules, network scanner, contacts, etc.
"""
import threading
import flet as ft
from typing import Optional, Dict, List
from datetime import datetime

from audio_modules.audio_io import (
    get_audio_interface, get_input_devices, get_output_devices,
    open_input_stream, open_output_stream, close_stream, close_audio_interface
)
from audio_modules.audio_sender import (
    send_audio, cleanup_sender, send_text_message,
    set_mute_state, stop_sender, reset_stop_flag as reset_sender_stop_flag
)
from audio_modules.audio_receiver import (
    receive_audio, cleanup_receiver, set_text_message_callback,
    set_deafen_state, set_incoming_call_callback, reset_receiver_socket,
    stop_receiver, reset_stop_flag as reset_receiver_stop_flag
)
from audio_modules.audio_filter import reset_noise_profile
from utils.connection_cache import (
    get_last_connection, get_last_microphone, get_last_speaker,
    has_cached_connection, save_cache,
)
from config.chat_history import (
    add_message, load_history, format_timestamp
)
from utils.network_scanner import (
    scan_network_async, format_device_list, extract_ip_from_formatted,
    get_local_ip
)
from config.contacts import (
    add_contact, get_all_contacts, get_contacts_display_list,
    extract_ip_from_contact_display, get_contact_name, search_contacts
)
from audio_modules.sound_effects import (
    sound_calling, sound_incoming, sound_connected, sound_rejected,
    sound_disconnected, sound_message, sound_cancelled, stop_all_sounds,
    set_call_volume, set_message_incoming_volume, set_message_outgoing_volume,
    get_call_volume, get_message_incoming_volume, get_message_outgoing_volume
)


# Protocol message constants
CMD_CALL_REQUEST = "__CALL_REQUEST__"
CMD_CALL_ACCEPT = "__CALL_ACCEPT__"
CMD_CALL_REJECT = "__CALL_REJECT__"
CMD_CALL_CANCEL = "__CALL_CANCEL__"
CMD_DISCONNECT = "__DISCONNECT__"

# Call states
STATE_IDLE = "idle"
STATE_CALLING = "calling"
STATE_RINGING = "ringing"
STATE_CONNECTED = "connected"


# Colors class for dialog styling
class Colors:
    BG_PRIMARY = "#36393f"
    BG_SECONDARY = "#2f3136"
    BG_TERTIARY = "#202225"
    BG_ACCENT = "#40444b"
    TEXT_PRIMARY = "#ffffff"
    TEXT_SECONDARY = "#b9bbbe"
    TEXT_MUTED = "#72767d"
    ACCENT_PRIMARY = "#5865f2"
    ACCENT_SUCCESS = "#3ba55d"
    ACCENT_DANGER = "#ed4245"
    ACCENT_WARNING = "#faa81a"


class HexChatBackend:
    """Backend logic handler for HexChat Flet app.
    
    Manages voice chat connections, audio streams, call handling,
    and message routing between UI and audio modules.
    """
    
    def __init__(self, layout):
        """Initialize backend with reference to UI layout.
        
        Args:
            layout: HexChatFletLayout instance for UI updates
        """
        self.layout = layout
        self.page = layout.page
        
        # Audio state
        self.audio_interface = None
        self.input_stream = None
        self.output_stream = None
        self.background_output_stream = None
        
        # Connection state
        self.target_ip = None
        self.is_muted = False
        self.is_deafened = False
        self.is_connected = False
        self.call_state = STATE_IDLE
        
        # Thread references
        self.receiver_thread = None
        self.sender_thread = None
        self.background_receiver_active = False
        
        # Device selection
        self.selected_device_index = None
        self.selected_output_device_index = None
        
        # Call handling
        self.incoming_call_ip = None
        self.calling_popup = None
        self.incoming_call_popup = None
        
        # Initialize
        self._load_cached_data()
        self.start_background_receiver()
    
    # ==================== INITIALIZATION ====================
    def _load_cached_data(self):
        """Load cached connection and device settings."""
        try:
            if has_cached_connection():
                cached_ip = get_last_connection()
                cached_mic = get_last_microphone()
                cached_speaker = get_last_speaker()
                
                self.target_ip = cached_ip
                self.selected_device_index = cached_mic
                self.selected_output_device_index = cached_speaker
                
                print(f"Loaded cache: IP={cached_ip}, Mic={cached_mic}, Speaker={cached_speaker}")
        except Exception as e:
            print(f"Could not load cache: {e}")
    
    def start_background_receiver(self):
        """Start background receiver thread to listen for incoming calls and messages.
        
        Creates a persistent audio stream and receiver thread that runs in the background,
        allowing the app to receive calls and messages even when not connected.
        """
        try:
            if not self.background_receiver_active:
                reset_receiver_socket()
                
                # Wrapper for receive_msg_update that accepts sender_ip
                def msg_callback_with_sender(message, sender_ip):
                    self.receive_msg_update(message, sender_ip)
                
                # Legacy callback without sender (for backward compatibility)
                def msg_callback_legacy(message):
                    self.receive_msg_update(message, None)
                
                set_text_message_callback(msg_callback_legacy, msg_callback_with_sender)
                set_incoming_call_callback(self.show_incoming_call)
                set_deafen_state(False)
                
                if self.background_output_stream:
                    try:
                        close_stream(self.background_output_stream)
                    except Exception:
                        pass
                
                temp_interface = get_audio_interface()
                self.background_output_stream = open_output_stream(
                    temp_interface,
                    self.selected_output_device_index
                )
                
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
    
    # ==================== CONNECTION MANAGEMENT ====================
    def connect(self):
        """Initiate a voice call to the selected contact.
        
        Validates target selection, sends call request, plays calling sound,
        and displays calling popup.
        """
        reset_receiver_stop_flag()
        reset_sender_stop_flag()
        
        if self.call_state == STATE_CALLING or self.is_connected:
            print("[!] Already in a call or connecting")
            return
        
        # ALWAYS get target from contacts dropdown
        contact_display = self.layout.contacts_dropdown.value
        if contact_display:
            ip = extract_ip_from_contact_display(contact_display)
            if ip:
                self.target_ip = ip
                print(f"[DEBUG] Calling selected contact: {contact_display} ({ip})")
            else:
                self.layout.add_system_message("General", "⚠️ No valid contact selected")
                self.page.update()
                return
        else:
            self.layout.add_system_message("General", "⚠️ No target IP selected. Choose a contact first.")
            self.page.update()
            return
        
        try:
            self.call_state = STATE_CALLING
            
            if not self.audio_interface:
                self.audio_interface = get_audio_interface()
            
            self.layout.add_system_message(
                "General",
                f"📞 CALLING {self.target_ip}..."
            )
            
            send_text_message(CMD_CALL_REQUEST, self.target_ip)
            sound_calling()
            
            self.layout.connect_btn.disabled = True
            self.layout.connect_btn.text = "Calling..."
            self.page.update()
            
            self.show_calling_popup(self.target_ip)
            
            print(f"[CALLING] {self.target_ip}...")
        except Exception as e:
            self.layout.add_system_message("General", f"❌ Error: {str(e)}")
            self.page.update()
            print(f"Connection error: {e}")
    
    def disconnect(self):
        """Disconnect from voice chat and clean up all resources."""
        try:
            import time
            
            # Notify peer of disconnection
            if self.is_connected and self.target_ip:
                try:
                    send_text_message(CMD_DISCONNECT, self.target_ip)
                except Exception as e:
                    print(f"Could not notify peer: {e}")
            
            # Clean up audio resources with individual error handling
            try:
                cleanup_sender()
            except Exception as e:
                print(f"Error cleaning up sender: {e}")
            
            try:
                cleanup_receiver()
            except Exception as e:
                print(f"Error cleaning up receiver: {e}")
            
            time.sleep(0.2)
            
            # Close streams safely
            if self.input_stream:
                try:
                    close_stream(self.input_stream)
                except Exception as e:
                    print(f"Error closing input stream: {e}")
                finally:
                    self.input_stream = None
            
            if self.output_stream and self.output_stream != self.background_output_stream:
                try:
                    close_stream(self.output_stream)
                except Exception as e:
                    print(f"Error closing output stream: {e}")
                finally:
                    self.output_stream = None
            
            if self.audio_interface:
                try:
                    close_audio_interface(self.audio_interface)
                except Exception as e:
                    print(f"Error closing audio interface: {e}")
                finally:
                    self.audio_interface = None
            
            # Update state
            self.is_connected = False
            self.call_state = STATE_IDLE
            
            # Update UI
            self._update_ui_idle("📴 Disconnected")
            
            sound_disconnected()
            
            # Restart background receiver
            self.background_receiver_active = False
            self.start_background_receiver()
            
            print("✓ Disconnected from voice chat")
        except Exception as e:
            print(f"Disconnect error: {e}")
            # Ensure state is reset even on error
            self.is_connected = False
            self.call_state = STATE_IDLE
            self.input_stream = None
            self.output_stream = None
            self.audio_interface = None
    
    # ==================== CALL HANDLING ====================
    def _is_self_call(self, caller_ip):
        """Check if call is from the same machine (self-call).
        
        Args:
            caller_ip: IP address of the caller
            
        Returns:
            bool: True if this is a self-call
        """
        local_ip = get_local_ip()
        return (caller_ip == local_ip or 
                caller_ip == "127.0.0.1" or 
                caller_ip == self.target_ip == local_ip)
    
    def _is_mutual_call(self, caller_ip):
        """Check if both parties are calling each other simultaneously.
        
        Args:
            caller_ip: IP address of the caller
            
        Returns:
            bool: True if this is a mutual call
        """
        is_self = self._is_self_call(caller_ip)
        return (self.call_state == STATE_CALLING and 
                (caller_ip == self.target_ip or is_self))
    
    def _setup_audio_connection(self, target_ip):
        """Setup audio streams and start sender thread.
        
        Args:
            target_ip: IP address to connect to
        """
        if not self.audio_interface:
            self.audio_interface = get_audio_interface()
        
        self.input_stream = open_input_stream(
            self.audio_interface,
            self.selected_device_index
        )
        self.output_stream = self.background_output_stream
        
        reset_noise_profile()
        set_deafen_state(self.is_deafened)
        save_cache(
            target_ip,
            self.selected_device_index,
            self.selected_output_device_index
        )
        
        self.sender_thread = threading.Thread(
            target=send_audio,
            args=(self.input_stream, self.output_stream, self.target_ip),
            daemon=True
        )
        self.sender_thread.start()
    
    def _update_ui_connected(self, message):
        """Update UI to connected state.
        
        Args:
            message: Message to display
        """
        self.layout.add_system_message("General", message)
        self.layout.connect_btn.disabled = True
        self.layout.connect_btn.text = "Connected!"
        self.layout.disconnect_btn.disabled = False
        self.page.update()
    
    def _update_ui_idle(self, message):
        """Update UI to idle state.
        
        Args:
            message: Message to display
        """
        self.layout.add_system_message("General", message)
        self.layout.connect_btn.disabled = False
        self.layout.connect_btn.text = "Connect Voice/Chat"
        self.layout.disconnect_btn.disabled = True
        self.page.update()
    
    def _get_display_name(self, ip):
        """Get display name for IP (contact name if exists, otherwise IP).
        
        Args:
            ip: IP address
            
        Returns:
            str: Contact name or IP address
        """
        contact_name = get_contact_name(ip)
        return contact_name if contact_name else ip
    
    def show_incoming_call(self, message, caller_ip):
        """Show incoming call notification and handle mutual call detection.
        
        Args:
            message: Protocol message (should be CMD_CALL_REQUEST)
            caller_ip: IP address of the caller
        """
        try:
            if message == CMD_CALL_REQUEST:
                # Check for mutual call or self-call scenario
                if self._is_mutual_call(caller_ip):
                    # Auto-accept mutual/self-call
                    print(f"[INFO] Mutual/self call detected with {caller_ip} - auto-accepting")
                    self._handle_mutual_call_accept(caller_ip)
                    return
                
                # Normal incoming call
                self.incoming_call_ip = caller_ip
                self.call_state = STATE_RINGING
                
                self.layout.add_system_message(
                    "General",
                    f"📞 Incoming call from {caller_ip}"
                )
                self.page.update()
                
                sound_incoming()
                self.show_incoming_call_popup(caller_ip)
                
                print(f"📞 Incoming call from {caller_ip}")
        except Exception as e:
            print(f"Error showing incoming call: {e}")
    
    def _handle_mutual_call_accept(self, caller_ip):
        """Handle auto-accept for mutual call scenario.
        
        Args:
            caller_ip: IP address of the caller
        """
        stop_all_sounds()
        self._close_all_call_popups()
        
        # Update state
        self.incoming_call_ip = None
        self.call_state = STATE_CONNECTED
        self.is_connected = True
        
        # Update UI
        self._update_ui_connected(f"✅ Mutual call - connected to {caller_ip}")
        
        # Setup audio in background thread
        def setup_audio():
            try:
                self._setup_audio_connection(caller_ip)
                send_text_message(CMD_CALL_ACCEPT, self.target_ip)
                sound_connected()
                print(f"✓ Mutual call connected with {caller_ip}")
            except Exception as e:
                print(f"Error in mutual call audio setup: {e}")
        
        threading.Thread(target=setup_audio, daemon=True).start()
    
    def show_incoming_call_popup(self, caller_ip):
        """Display incoming call dialog with accept/reject buttons.
        
        Args:
            caller_ip: IP address of the incoming caller
        """
        display_name = self._get_display_name(caller_ip)
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("📞 Incoming Call", size=20, weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(f"From: {display_name}", size=16),
                    ft.Text(f"IP: {caller_ip}", size=14, color=Colors.TEXT_SECONDARY),
                ], tight=True, spacing=10),
                padding=20,
            ),
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        def accept_call(e):
            print("[DEBUG] Accept button clicked")
            self.accept_call()
        
        def reject_call(e):
            print("[DEBUG] Reject button clicked")
            self.reject_call()
        
        dialog.actions = [
            ft.ElevatedButton(
                "✅ Accept",
                on_click=accept_call,
                bgcolor=Colors.ACCENT_SUCCESS,
                color=Colors.TEXT_PRIMARY,
            ),
            ft.ElevatedButton(
                "❌ Reject",
                on_click=reject_call,
                bgcolor=Colors.ACCENT_DANGER,
                color=Colors.TEXT_PRIMARY,
            ),
        ]
        
        self.incoming_call_popup = dialog
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
    
    def show_calling_popup(self, target_ip):
        """Display outgoing call dialog with cancel button.
        
        Args:
            target_ip: IP address being called
        """
        display_name = self._get_display_name(target_ip)
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("📞 Calling...", size=20, weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(f"Calling: {display_name}", size=16),
                    ft.Text(f"IP: {target_ip}", size=14, color=Colors.TEXT_SECONDARY),
                    ft.ProgressRing(),
                ], tight=True, spacing=15, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=20,
            ),
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        def cancel_call(e):
            print("[DEBUG] Cancel button clicked")
            self.cancel_call()
        
        dialog.actions = [
            ft.ElevatedButton(
                "Cancel",
                on_click=cancel_call,
                bgcolor=Colors.ACCENT_DANGER,
                color=Colors.TEXT_PRIMARY,
            ),
        ]
        
        self.calling_popup = dialog
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
    
    def _close_all_call_popups(self):
        """Close all active call dialogs (incoming and outgoing)."""
        try:
            stop_all_sounds()
            
            # Close incoming call popup
            if self.incoming_call_popup:
                try:
                    self.incoming_call_popup.open = False
                except Exception as ex:
                    print(f"Error closing incoming popup: {ex}")
                self.incoming_call_popup = None
            
            # Close calling popup
            if self.calling_popup:
                try:
                    self.calling_popup.open = False
                except Exception as ex:
                    print(f"Error closing calling popup: {ex}")
                self.calling_popup = None
            
            self.page.update()
        except Exception as e:
            print(f"Error closing popups: {e}")
            import traceback
            traceback.print_exc()
    
    def accept_call(self):
        """Accept incoming call and establish audio connection.
        
        Closes call popup, sets up audio streams in background thread,
        and notifies the caller that the call was accepted.
        """
        try:
            reset_receiver_stop_flag()
            reset_sender_stop_flag()
            
            if not self.incoming_call_ip:
                print("[ERROR] No incoming_call_ip set")
                return
            
            caller_ip = self.incoming_call_ip
            
            # Close all popups FIRST
            self._close_all_call_popups()
            
            self.target_ip = caller_ip
            self.call_state = STATE_CONNECTED
            self.incoming_call_ip = None
            self.is_connected = True
            
            # Update UI immediately
            self._update_ui_connected(f"✅ Call accepted with {caller_ip}")
            
            # Run audio setup in background thread to not block UI
            def setup_audio():
                try:
                    self._setup_audio_connection(caller_ip)
                    send_text_message(CMD_CALL_ACCEPT, self.target_ip)
                    sound_connected()
                    print(f"✓ Call accepted from {caller_ip}")
                except Exception as e:
                    print(f"Error in audio setup: {e}")
            
            threading.Thread(target=setup_audio, daemon=True).start()
            
        except Exception as e:
            print(f"Error accepting call: {e}")
    
    def reject_call(self):
        """Reject incoming call and notify the caller."""
        try:
            if not self.incoming_call_ip:
                return
            
            caller_ip = self.incoming_call_ip
            
            # Close all popups FIRST
            self._close_all_call_popups()
            
            send_text_message(CMD_CALL_REJECT, caller_ip)
            
            self.incoming_call_ip = None
            self.call_state = STATE_IDLE
            
            self.layout.add_system_message("General", "❌ Call rejected")
            self.page.update()
            
            sound_rejected()
            
            print(f"✓ Call rejected from {caller_ip}")
        except Exception as e:
            print(f"Error rejecting call: {e}")
    
    def cancel_call(self):
        """Cancel outgoing call and clean up resources."""
        try:
            target_ip = self.target_ip
            
            stop_all_sounds()
            self._close_all_call_popups()
            
            if target_ip:
                try:
                    send_text_message(CMD_CALL_CANCEL, target_ip)
                except Exception as e:
                    print(f"Could not notify peer: {e}")
            
            # Clean up with individual error handling
            try:
                cleanup_receiver()
            except Exception as e:
                print(f"Error cleaning up receiver: {e}")
            
            if self.output_stream:
                try:
                    close_stream(self.output_stream)
                except Exception as e:
                    print(f"Error closing stream: {e}")
                finally:
                    self.output_stream = None
            
            if self.audio_interface:
                try:
                    close_audio_interface(self.audio_interface)
                except Exception as e:
                    print(f"Error closing interface: {e}")
                finally:
                    self.audio_interface = None
            
            self.call_state = STATE_IDLE
            self.target_ip = None
            self.incoming_call_ip = None
            
            self._update_ui_idle("❌ Call cancelled")
            
            sound_cancelled()
            
            self.background_receiver_active = False
            self.start_background_receiver()
            
            print(f"✓ Call cancelled to {target_ip}")
        except Exception as e:
            print(f"Error cancelling call: {e}")
    
    # ==================== MESSAGE HANDLING ====================
    def receive_msg_update(self, message, sender_ip=None):
        """Handle received protocol messages and text messages.
        
        Args:
            message: The message content or protocol command
            sender_ip: IP address of the sender (for validation)
        """
        if message == CMD_CALL_ACCEPT:
            # Validate sender - must be from the person we're calling
            if sender_ip and self.target_ip and sender_ip != self.target_ip:
                print(f"[SECURITY] Ignoring {CMD_CALL_ACCEPT} from {sender_ip}, expected {self.target_ip}")
                return
            
            if self.call_state == STATE_CALLING:
                # Close all popups
                self._close_all_call_popups()
                
                self.call_state = STATE_CONNECTED
                self.is_connected = True
                
                self._update_ui_connected(f"✅ Connected to {self.target_ip}")
                
                sound_connected()
                
                # Start audio streams
                try:
                    self._setup_audio_connection(self.target_ip)
                except Exception as e:
                    print(f"Error starting audio: {e}")
        
        elif message == CMD_CALL_REJECT:
            # Validate sender - must be from the person we're calling
            if sender_ip and self.target_ip and sender_ip != self.target_ip:
                print(f"[SECURITY] Ignoring {CMD_CALL_REJECT} from {sender_ip}, expected {self.target_ip}")
                return
            
            if self.call_state == STATE_CALLING:
                # Close all popups
                self._close_all_call_popups()
                
                self.call_state = STATE_IDLE
                self.target_ip = None
                self._update_ui_idle("❌ Call rejected by friend")
                
                sound_rejected()
                
                cleanup_receiver()
        
        elif message == CMD_CALL_CANCEL:
            # Validate sender - must be from the person who called us
            if sender_ip and self.incoming_call_ip and sender_ip != self.incoming_call_ip:
                print(f"[SECURITY] Ignoring {CMD_CALL_CANCEL} from {sender_ip}, expected {self.incoming_call_ip}")
                return
            
            if self.call_state == STATE_RINGING:
                # Close all popups
                self._close_all_call_popups()
                
                self.call_state = STATE_IDLE
                self.incoming_call_ip = None
                self.layout.add_system_message("General", "❌ Call cancelled by friend")
                self.page.update()
                
                sound_cancelled()
        
        elif message == CMD_DISCONNECT:
            # Validate sender - must be from connected peer
            if sender_ip and self.target_ip and sender_ip != self.target_ip:
                print(f"[SECURITY] Ignoring {CMD_DISCONNECT} from {sender_ip}, expected {self.target_ip}")
                return
            
            self.layout.add_system_message("General", "📴 Friend disconnected")
            self.page.update()
            
            sound_disconnected()
            
            if self.is_connected:
                self.disconnect()
        else:
            # Regular text message
            timestamp = datetime.now().isoformat()
            # Find which chat tab to add to - use sender IP if available, else target_ip
            chat_name = sender_ip if sender_ip else (self.target_ip if self.target_ip else "General")
            
            # Ensure chat tab exists
            if chat_name != "General" and chat_name not in self.layout.chat_tabs:
                contact_name = get_contact_name(chat_name)
                display = f"{contact_name} - {chat_name}" if contact_name else chat_name
                self.layout.switch_to_chat_tab(display)
            
            self.layout.add_message_to_chat(chat_name, "Friend", message, timestamp)
            self.page.update()
            
            sound_message()
            
            # Save to history using sender_ip if available
            history_ip = sender_ip if sender_ip else self.target_ip
            if history_ip:
                add_message(history_ip, "Friend", message)
    
    def send_message(self):
        """Send text message to selected contact.
        
        Validates target selection, sends message, and updates UI.
        Creates chat tab if it doesn't exist.
        """
        message = self.layout.message_input.value
        if not message:
            return
        
        # Get the target from dropdown or current chat
        target_display = self.layout.chat_target_dropdown.value
        if not target_display or target_display == "General":
            if not self.target_ip:
                self.layout.add_system_message("General", "⚠️ No target IP selected. Choose from 'Chat with' dropdown.")
                self.layout.message_input.value = ""
                self.page.update()
                return
            # Use current target_ip
            chat_name = "General"
        else:
            # Extract IP from selected contact
            ip = extract_ip_from_contact_display(target_display)
            if ip:
                self.target_ip = ip
                chat_name = ip
            else:
                self.layout.add_system_message("General", "⚠️ Invalid contact selected")
                self.layout.message_input.value = ""
                self.page.update()
                return
        
        try:
            send_text_message(message, self.target_ip)
            
            timestamp = datetime.now().isoformat()
            
            # Ensure chat tab exists for this contact
            if chat_name != "General" and chat_name not in self.layout.chat_tabs:
                # Create the tab by switching to it first
                contact_name = get_contact_name(chat_name)
                display = f"{contact_name} - {chat_name}" if contact_name else chat_name
                self.layout.switch_to_chat_tab(display)
            
            # Add message to the correct chat
            self.layout.add_message_to_chat(chat_name, "You", message, timestamp)
            self.layout.message_input.value = ""
            self.page.update()
            
            if self.target_ip:
                add_message(self.target_ip, "You", message)
            
            print(f"✓ Message sent to {self.target_ip}: {message} (displayed in {chat_name})")
        except Exception as e:
            self.layout.add_system_message("General", f"❌ Error sending message: {e}")
            self.page.update()
    
    # ==================== AUDIO CONTROLS ====================
    def toggle_mute(self):
        """Toggle microphone mute state and update UI."""
        self.is_muted = not self.is_muted
        set_mute_state(self.is_muted)
        
        status = "🔇 Muted" if self.is_muted else "🎤 Unmuted"
        self.layout.add_system_message("General", status)
        self.layout.mute_switch.value = self.is_muted
        self.page.update()
    
    def toggle_deafen(self):
        """Toggle speaker deafen state and update UI."""
        self.is_deafened = not self.is_deafened
        set_deafen_state(self.is_deafened)
        
        status = "🔇 Deafened" if self.is_deafened else "🔊 Listening"
        self.layout.add_system_message("General", status)
        self.layout.deafen_switch.value = self.is_deafened
        self.page.update()
    
    # ==================== CONTACTS & NETWORK ====================
    def refresh_contacts(self):
        """Reload and update contacts list in UI."""
        contacts = get_contacts_display_list()
        self.layout.update_contacts_list(contacts)
        self.page.update()
    
    def select_contact(self, contact_display):
        """Select a contact as the current call/chat target.
        
        Args:
            contact_display: Contact display string from dropdown
        """
        ip = extract_ip_from_contact_display(contact_display)
        if ip:
            self.target_ip = ip
            display = self._get_display_name(ip)
            self.layout.add_system_message("General", f"📌 Selected: {display}")
            self.page.update()


