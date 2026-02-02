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
    """Backend logic handler for HexChat Flet app."""
    
    def __init__(self, layout):
        """Initialize backend with reference to UI layout."""
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
        self.call_state = "idle"  # idle, calling, ringing, connected
        
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
        """Start background listener for incoming calls."""
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
        """Initiate a voice call to the target IP."""
        reset_receiver_stop_flag()
        reset_sender_stop_flag()
        
        if self.call_state == "calling" or self.is_connected:
            print("[!] Already in a call or connecting")
            return
        
        # ALWAYS get target from contacts dropdown
        contact_display = self.layout.contacts_dropdown.value
        if contact_display:
            from config.contacts import extract_ip_from_contact_display
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
            self.call_state = "calling"
            
            if not self.audio_interface:
                self.audio_interface = get_audio_interface()
            
            timestamp = datetime.now().isoformat()
            self.layout.add_system_message(
                "General",
                f"📞 CALLING {self.target_ip}..."
            )
            
            send_text_message("__CALL_REQUEST__", self.target_ip)
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
        """Disconnect from voice chat."""
        try:
            import time
            
            if self.is_connected and self.target_ip:
                try:
                    send_text_message("__DISCONNECT__", self.target_ip)
                except Exception:
                    pass
            
            cleanup_sender()
            cleanup_receiver()
            time.sleep(0.2)
            
            if self.input_stream:
                close_stream(self.input_stream)
                self.input_stream = None
            if self.output_stream and self.output_stream != self.background_output_stream:
                close_stream(self.output_stream)
            self.output_stream = None
            
            if self.audio_interface:
                close_audio_interface(self.audio_interface)
                self.audio_interface = None
            
            self.is_connected = False
            self.call_state = "idle"
            
            self.layout.add_system_message("General", "📴 Disconnected")
            self.layout.connect_btn.disabled = False
            self.layout.connect_btn.text = "Connect Voice/Chat"
            self.layout.disconnect_btn.disabled = True
            self.page.update()
            
            sound_disconnected()
            
            self.background_receiver_active = False
            self.start_background_receiver()
            
            print("✓ Disconnected from voice chat")
        except Exception as e:
            print(f"Disconnect error: {e}")
    
    # ==================== CALL HANDLING ====================
    def show_incoming_call(self, message, caller_ip):
        """Show incoming call notification."""
        try:
            if message == "__CALL_REQUEST__":
                # Get local IP for self-call detection
                local_ip = get_local_ip()
                
                # Check for self-call (calling your own machine)
                is_self_call = (caller_ip == local_ip or 
                               caller_ip == "127.0.0.1" or 
                               caller_ip == self.target_ip == local_ip)
                
                # Check for mutual call scenario (both users calling each other)
                is_mutual_call = (self.call_state == "calling" and 
                                 (caller_ip == self.target_ip or is_self_call))
                
                if is_mutual_call:
                    # Mutual call or self-call detected - auto-accept immediately
                    print(f"[DEBUG] Mutual/self call detected with {caller_ip} - auto-accepting")
                    stop_all_sounds()  # Stop the calling sound
                    
                    # Close calling popup if open
                    self._close_all_call_popups()
                    
                    # Set state to connected
                    self.incoming_call_ip = None
                    self.call_state = "connected"
                    self.is_connected = True
                    
                    # Update UI
                    self.layout.add_system_message(
                        "General",
                        f"✅ Mutual call - connected to {caller_ip}"
                    )
                    self.layout.connect_btn.disabled = True
                    self.layout.connect_btn.text = "Connected!"
                    self.layout.disconnect_btn.disabled = False
                    self.page.update()
                    
                    # Start audio in background
                    def setup_mutual_call_audio():
                        try:
                            if not self.audio_interface:
                                self.audio_interface = get_audio_interface()
                            
                            self.input_stream = open_input_stream(
                                self.audio_interface,
                                self.selected_device_index
                            )
                            self.output_stream = self.background_output_stream
                            
                            reset_noise_profile()
                            save_cache(
                                caller_ip,
                                self.selected_device_index,
                                self.selected_output_device_index
                            )
                            
                            self.sender_thread = threading.Thread(
                                target=send_audio,
                                args=(self.input_stream, self.output_stream, self.target_ip),
                                daemon=True
                            )
                            self.sender_thread.start()
                            
                            # Send accept to complete handshake
                            send_text_message("__CALL_ACCEPT__", self.target_ip)
                            
                            sound_connected()
                            print(f"✓ Mutual call connected with {caller_ip}")
                        except Exception as e:
                            print(f"Error in mutual call audio setup: {e}")
                    
                    threading.Thread(target=setup_mutual_call_audio, daemon=True).start()
                    return
                
                # Normal incoming call
                self.incoming_call_ip = caller_ip
                self.call_state = "ringing"
                
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
    
    def show_incoming_call_popup(self, caller_ip):
        """Show incoming call dialog."""
        contact_name = get_contact_name(caller_ip)
        display_name = contact_name if contact_name else caller_ip
        
        # Create dialog first
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
            # Let accept_call handle all the cleanup
            print("[DEBUG] Accept button clicked")
            self.accept_call()
        
        def reject_call(e):
            # Let reject_call handle all the cleanup
            print("[DEBUG] Reject button clicked")
            self.reject_call()
        
        # Add buttons with callbacks
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
        print("[DEBUG] Incoming call popup opened")
    
    def show_calling_popup(self, target_ip):
        """Show outgoing call dialog."""
        contact_name = get_contact_name(target_ip)
        display_name = contact_name if contact_name else target_ip
        
        # Create dialog first
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
            # Let cancel_call handle all the cleanup
            print("[DEBUG] Cancel button clicked")
            self.cancel_call()
        
        # Add cancel button with the callback
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
        print(f"[DEBUG] Calling popup opened for {target_ip}")
    
    def _close_all_call_popups(self):
        """Helper to close all call-related popups immediately."""
        try:
            # Stop any call sounds first
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
            print("[DEBUG] All popups closed")
        except Exception as e:
            print(f"Error closing popups: {e}")
            import traceback
            traceback.print_exc()
    
    def accept_call(self):
        """Accept incoming call."""
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
            self.call_state = "connected"
            self.incoming_call_ip = None
            self.is_connected = True
            
            # Update UI immediately
            self.layout.add_system_message(
                "General",
                f"✅ Call accepted with {caller_ip}"
            )
            self.layout.connect_btn.disabled = True
            self.layout.connect_btn.text = "Connected!"
            self.layout.disconnect_btn.disabled = False
            self.page.update()
            
            # Run audio setup in background thread to not block UI
            def setup_audio():
                try:
                    self.audio_interface = get_audio_interface()
                    self.input_stream = open_input_stream(
                        self.audio_interface,
                        self.selected_device_index
                    )
                    self.output_stream = self.background_output_stream
                    
                    save_cache(
                        caller_ip,
                        self.selected_device_index,
                        self.selected_output_device_index
                    )
                    
                    reset_noise_profile()
                    set_deafen_state(self.is_deafened)
                    
                    self.sender_thread = threading.Thread(
                        target=send_audio,
                        args=(self.input_stream, self.output_stream, self.target_ip),
                        daemon=True
                    )
                    self.sender_thread.start()
                    
                    send_text_message("__CALL_ACCEPT__", self.target_ip)
                    
                    sound_connected()
                    
                    print(f"✓ Call accepted from {caller_ip}")
                except Exception as e:
                    print(f"Error in audio setup: {e}")
            
            threading.Thread(target=setup_audio, daemon=True).start()
            
        except Exception as e:
            print(f"Error accepting call: {e}")
    
    def reject_call(self):
        """Reject incoming call."""
        try:
            if not self.incoming_call_ip:
                return
            
            caller_ip = self.incoming_call_ip
            
            # Close all popups FIRST
            self._close_all_call_popups()
            
            send_text_message("__CALL_REJECT__", caller_ip)
            
            self.incoming_call_ip = None
            self.call_state = "idle"
            
            self.layout.add_system_message("General", "❌ Call rejected")
            self.page.update()
            
            sound_rejected()
            
            print(f"✓ Call rejected from {caller_ip}")
        except Exception as e:
            print(f"Error rejecting call: {e}")
    
    def cancel_call(self):
        """Cancel outgoing call."""
        try:
            target_ip = self.target_ip
            
            # Stop all sounds first (calling ringtone)
            stop_all_sounds()
            
            # Close all popups using the helper method
            self._close_all_call_popups()
            
            if target_ip:
                send_text_message("__CALL_CANCEL__", target_ip)
            
            cleanup_receiver()
            if self.output_stream:
                close_stream(self.output_stream)
                self.output_stream = None
            if self.audio_interface:
                close_audio_interface(self.audio_interface)
                self.audio_interface = None
            
            self.call_state = "idle"
            self.target_ip = None
            self.incoming_call_ip = None
            
            self.layout.add_system_message("General", "❌ Call cancelled")
            self.layout.connect_btn.disabled = False
            self.layout.connect_btn.text = "Connect Voice/Chat"
            self.page.update()
            
            sound_cancelled()
            
            self.background_receiver_active = False
            self.start_background_receiver()
            
            print(f"✓ Call cancelled to {target_ip}")
        except Exception as e:
            print(f"Error cancelling call: {e}")
    
    # ==================== MESSAGE HANDLING ====================
    def receive_msg_update(self, message, sender_ip=None):
        """Handle received messages.
        
        Args:
            message: The message content
            sender_ip: IP address of the sender (for validation)
        """
        if message == "__CALL_ACCEPT__":
            # Validate sender - must be from the person we're calling
            if sender_ip and self.target_ip and sender_ip != self.target_ip:
                print(f"[SECURITY] Ignoring __CALL_ACCEPT__ from {sender_ip}, expected {self.target_ip}")
                return
            
            if self.call_state == "calling":
                # Close all popups
                self._close_all_call_popups()
                
                self.call_state = "connected"
                self.is_connected = True
                
                self.layout.add_system_message(
                    "General",
                    f"✅ Connected to {self.target_ip}"
                )
                self.layout.connect_btn.disabled = True
                self.layout.connect_btn.text = "Connected!"
                self.layout.disconnect_btn.disabled = False
                self.page.update()
                
                sound_connected()
                
                # Start audio streams
                try:
                    if not self.audio_interface:
                        self.audio_interface = get_audio_interface()
                    
                    self.input_stream = open_input_stream(
                        self.audio_interface,
                        self.selected_device_index
                    )
                    self.output_stream = self.background_output_stream
                    
                    reset_noise_profile()
                    save_cache(
                        self.target_ip,
                        self.selected_device_index,
                        self.selected_output_device_index
                    )
                    
                    self.sender_thread = threading.Thread(
                        target=send_audio,
                        args=(self.input_stream, self.output_stream, self.target_ip),
                        daemon=True
                    )
                    self.sender_thread.start()
                except Exception as e:
                    print(f"Error starting audio: {e}")
        
        elif message == "__CALL_REJECT__":
            # Validate sender - must be from the person we're calling
            if sender_ip and self.target_ip and sender_ip != self.target_ip:
                print(f"[SECURITY] Ignoring __CALL_REJECT__ from {sender_ip}, expected {self.target_ip}")
                return
            
            if self.call_state == "calling":
                # Close all popups
                self._close_all_call_popups()
                
                self.call_state = "idle"
                self.target_ip = None
                self.layout.add_system_message("General", "❌ Call rejected by friend")
                self.layout.connect_btn.disabled = False
                self.layout.connect_btn.text = "Connect Voice/Chat"
                self.page.update()
                
                sound_rejected()
                
                cleanup_receiver()
        
        elif message == "__CALL_CANCEL__":
            # Validate sender - must be from the person who called us
            if sender_ip and self.incoming_call_ip and sender_ip != self.incoming_call_ip:
                print(f"[SECURITY] Ignoring __CALL_CANCEL__ from {sender_ip}, expected {self.incoming_call_ip}")
                return
            
            if self.call_state == "ringing":
                # Close all popups
                self._close_all_call_popups()
                
                self.call_state = "idle"
                self.incoming_call_ip = None
                self.layout.add_system_message("General", "❌ Call cancelled by friend")
                self.page.update()
                
                sound_cancelled()
        
        elif message == "__DISCONNECT__":
            # Validate sender - must be from connected peer
            if sender_ip and self.target_ip and sender_ip != self.target_ip:
                print(f"[SECURITY] Ignoring __DISCONNECT__ from {sender_ip}, expected {self.target_ip}")
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
                from config.contacts import get_contact_name
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
        """Send text message."""
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
            from config.contacts import extract_ip_from_contact_display
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
                from config.contacts import get_contact_name
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
        """Toggle microphone mute."""
        self.is_muted = not self.is_muted
        set_mute_state(self.is_muted)
        
        status = "🔇 Muted" if self.is_muted else "🎤 Unmuted"
        self.layout.add_system_message("General", status)
        self.layout.mute_switch.value = self.is_muted
        self.page.update()
    
    def toggle_deafen(self):
        """Toggle speaker deafen."""
        self.is_deafened = not self.is_deafened
        set_deafen_state(self.is_deafened)
        
        status = "🔇 Deafened" if self.is_deafened else "🔊 Listening"
        self.layout.add_system_message("General", status)
        self.layout.deafen_switch.value = self.is_deafened
        self.page.update()
    
    # ==================== CONTACTS & NETWORK ====================
    def refresh_contacts(self):
        """Reload contacts list."""
        contacts = get_contacts_display_list()
        self.layout.update_contacts_list(contacts)
        self.page.update()
    
    def select_contact(self, contact_display):
        """Select a contact to connect to."""
        ip = extract_ip_from_contact_display(contact_display)
        if ip:
            self.target_ip = ip
            contact_name = get_contact_name(ip)
            display = contact_name if contact_name else ip
            self.layout.add_system_message("General", f"📌 Selected: {display}")
            self.page.update()


