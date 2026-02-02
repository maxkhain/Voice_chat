# HexChat P2P - Calling Logic Flow Documentation

This document describes the complete calling workflow in HexChat P2P, from selecting a contact to managing call states (accept, reject, cancel).

---

## Table of Contents

1. [Overview](#overview)
2. [Call States](#call-states)
3. [Selecting a Contact](#1-selecting-a-contact)
4. [Initiating a Call (Caller Side)](#2-initiating-a-call-caller-side)
5. [Receiving a Call (Callee Side)](#3-receiving-a-call-callee-side)
6. [Accepting a Call](#4-accepting-a-call)
7. [Rejecting a Call](#5-rejecting-a-call)
8. [Cancelling a Call](#6-cancelling-a-call)
9. [Disconnecting](#7-disconnecting)
10. [Message Protocol](#message-protocol)
11. [UI Components](#ui-components)

---

## Overview

HexChat P2P uses a peer-to-peer architecture for voice/text communication. The calling system uses special control messages sent via `send_text_message()` to signal call states between peers.

### Key Files
- `ui_modules/ui_backend_flet.py` - Backend logic for call handling
- `ui_modules/ui_layout_flet.py` - UI components and dialogs
- `audio_modules/audio_sender.py` - Audio transmission
- `audio_modules/audio_receiver.py` - Audio reception and incoming call detection

---

## Call States

The application tracks call state using `self.call_state`:

| State | Description |
|-------|-------------|
| `idle` | No active call, ready to call or receive |
| `calling` | Outgoing call in progress, waiting for response |
| `ringing` | Incoming call detected, waiting for user action |
| `connected` | Call active, audio streaming both ways |

Additional state variables:
- `self.is_connected` (bool) - True when call is established
- `self.target_ip` - IP address of the call target/peer
- `self.incoming_call_ip` - IP address of incoming caller

---

## 1. Selecting a Contact

### UI Components
- **Contacts Dropdown** (`self.layout.contacts_dropdown`) - Shows saved contacts

### Flow

```
User Action: Select contact from dropdown
         ↓
UI Event: contacts_dropdown.on_change triggered
         ↓
Callback: self.on_contact_selected(contact_display)
         ↓
Backend: select_contact() method called
         ↓
Actions:
  1. Extract IP from contact display string
  2. Set self.target_ip = extracted IP
  3. Display system message "📌 Selected: {contact_name}"
```

### Code Reference
```python
def select_contact(self, contact_display):
    """Select a contact to connect to."""
    ip = extract_ip_from_contact_display(contact_display)
    if ip:
        self.target_ip = ip
        contact_name = get_contact_name(ip)
        display = contact_name if contact_name else ip
        self.layout.add_system_message("General", f"📌 Selected: {display}")
```

---

## 2. Initiating a Call (Caller Side)

### UI Components
- **Connect Button** (`self.layout.connect_btn`) - "Connect Voice/Chat"

### Prerequisites
- A contact must be selected in the dropdown
- `call_state` must be `idle`
- Must not already be connected

### Flow

```
User Action: Click "Connect Voice/Chat" button
         ↓
Callback: self.on_connect_click() → connect()
         ↓
Validation:
  ├── Check if already calling/connected → return
  └── Check if contact selected → error if not
         ↓
Set State:
  └── call_state = "calling"
         ↓
Initialize Audio:
  └── Get audio interface if not exists
         ↓
Send Control Message:
  └── send_text_message("__CALL_REQUEST__", target_ip)
         ↓
Play Sound:
  └── sound_calling()
         ↓
Update UI:
  ├── Disable connect button
  ├── Set button text to "Calling..."
  └── Add system message "📞 CALLING {ip}..."
         ↓
Show Popup:
  └── show_calling_popup(target_ip)
```

### Calling Popup Dialog
- **Title**: "📞 Calling..."
- **Content**: Contact name and IP with progress spinner
- **Actions**: Cancel button to abort the call

---

## 3. Receiving a Call (Callee Side)

### Background Receiver
The app runs a background receiver thread that listens for incoming calls at all times.

```python
def start_background_receiver(self):
    # Sets up callbacks for:
    set_text_message_callback(self.receive_msg_update, ...)
    set_incoming_call_callback(self.show_incoming_call)
```

### Flow

```
Event: Receive "__CALL_REQUEST__" message
         ↓
Callback: show_incoming_call(message, caller_ip)
         ↓
Validation:
  └── Check message == "__CALL_REQUEST__"
         ↓
Set State:
  ├── self.incoming_call_ip = caller_ip
  └── self.call_state = "ringing"
         ↓
Update UI:
  └── Add system message "📞 Incoming call from {ip}"
         ↓
Play Sound:
  └── sound_incoming()
         ↓
Show Popup:
  └── show_incoming_call_popup(caller_ip)
```

### Incoming Call Popup Dialog
- **Title**: "📞 Incoming Call"
- **Content**: Caller's contact name (if saved) and IP address
- **Actions**: 
  - ✅ Accept (green button)
  - ❌ Reject (red button)

---

## 4. Accepting a Call

### Triggered By
- User clicks "✅ Accept" in incoming call popup

### Flow

```
User Action: Click "Accept" button
         ↓
Callback: accept_call()
         ↓
Reset Flags:
  ├── reset_receiver_stop_flag()
  └── reset_sender_stop_flag()
         ↓
Validation:
  └── Check incoming_call_ip exists
         ↓
Close Popups:
  └── _close_all_call_popups()
         ↓
Set State:
  ├── self.target_ip = caller_ip
  ├── self.call_state = "connected"
  ├── self.incoming_call_ip = None
  └── self.is_connected = True
         ↓
Update UI (Immediate):
  ├── Add system message "✅ Call accepted with {ip}"
  ├── Disable connect button
  ├── Set button text to "Connected!"
  └── Enable disconnect button
         ↓
Background Thread - Audio Setup:
  ├── Initialize audio interface
  ├── Open input stream (microphone)
  ├── Set output stream (speakers)
  ├── Save connection to cache
  ├── Reset noise profile
  ├── Set deafen state
  ├── Start sender thread (send_audio)
  └── Send "__CALL_ACCEPT__" to caller
         ↓
Play Sound:
  └── sound_connected()
```

### What Happens on Caller Side
When caller receives `__CALL_ACCEPT__`:

```
Event: receive_msg_update("__CALL_ACCEPT__")
         ↓
Condition: call_state == "calling"
         ↓
Close Popups:
  └── _close_all_call_popups()
         ↓
Set State:
  ├── call_state = "connected"
  └── is_connected = True
         ↓
Update UI:
  ├── Add system message "✅ Connected to {ip}"
  ├── Disable connect button
  ├── Set button text to "Connected!"
  └── Enable disconnect button
         ↓
Play Sound:
  └── sound_connected()
         ↓
Start Audio:
  ├── Initialize audio interface
  ├── Open input/output streams
  ├── Reset noise profile
  ├── Save to cache
  └── Start sender thread
```

---

## 5. Rejecting a Call

### Triggered By
- User clicks "❌ Reject" in incoming call popup

### Callee Side Flow (Person Rejecting)

```
User Action: Click "Reject" button
         ↓
Callback: reject_call()
         ↓
Validation:
  └── Check incoming_call_ip exists
         ↓
Close Popups:
  └── _close_all_call_popups()
         ↓
Send Control Message:
  └── send_text_message("__CALL_REJECT__", caller_ip)
         ↓
Set State:
  ├── self.incoming_call_ip = None
  └── self.call_state = "idle"
         ↓
Update UI:
  └── Add system message "❌ Call rejected"
         ↓
Play Sound:
  └── sound_rejected()
         ↓
Return to Idle:
  └── Ready to receive/make new calls
```

### Caller Side Flow (Person Who Called)

When caller receives `__CALL_REJECT__`:

```
Event: receive_msg_update("__CALL_REJECT__")
         ↓
Condition Check:
  └── call_state == "calling" ? (must be true to proceed)
         ↓
Close Popups:
  └── _close_all_call_popups()
         ↓
Set State:
  ├── call_state = "idle"
  └── target_ip = None
         ↓
Update UI:
  ├── Add system message "❌ Call rejected by friend"
  ├── Enable connect button
  └── Set button text to "Connect Voice/Chat"
         ↓
Play Sound:
  └── sound_rejected()
         ↓
Cleanup:
  └── cleanup_receiver()
         ↓
Return to Idle:
  └── Ready to make/receive new calls
```

---

## 6. Cancelling a Call

### Triggered By
- User clicks "Cancel" in outgoing call popup

### Caller Side Flow (Person Cancelling)

```
User Action: Click "Cancel" button
         ↓
Callback: cancel_call()
         ↓
Close Popups:
  └── _close_all_call_popups()
         ↓
Send Control Message:
  └── send_text_message("__CALL_CANCEL__", target_ip)
         ↓
Cleanup Audio:
  ├── cleanup_receiver()
  ├── Close output stream
  └── Close audio interface
         ↓
Set State:
  ├── call_state = "idle"
  ├── target_ip = None
  └── incoming_call_ip = None
         ↓
Update UI:
  ├── Add system message "❌ Call cancelled"
  ├── Enable connect button
  └── Set button text to "Connect Voice/Chat"
         ↓
Play Sound:
  └── sound_cancelled()
         ↓
Restart Background:
  └── start_background_receiver()
         ↓
Return to Idle:
  └── Ready to make/receive new calls
```

### Callee Side Flow (Person Who Was Being Called)

When callee receives `__CALL_CANCEL__`:

```
Event: receive_msg_update("__CALL_CANCEL__")
         ↓
Condition Check:
  └── call_state == "ringing" ? (must be true to proceed)
         ↓
Close Popups:
  └── _close_all_call_popups()
         ↓
Set State:
  ├── call_state = "idle"
  └── incoming_call_ip = None
         ↓
Update UI:
  └── Add system message "❌ Call cancelled by friend"
         ↓
Play Sound:
  └── sound_cancelled()
         ↓
Return to Idle:
  └── Background receiver already running
  └── Ready to receive new calls
```

---

## 7. Disconnecting

### Triggered By
- User clicks "Disconnect" button during active call

### Flow

```
User Action: Click "Disconnect" button
         ↓
Callback: disconnect()
         ↓
Send Control Message (if connected):
  └── send_text_message("__DISCONNECT__", target_ip)
         ↓
Cleanup:
  ├── cleanup_sender()
  ├── cleanup_receiver()
  ├── Wait 0.2 seconds
  ├── Close input stream
  ├── Close output stream
  └── Close audio interface
         ↓
Set State:
  ├── is_connected = False
  └── call_state = "idle"
         ↓
Update UI:
  ├── Add system message "📴 Disconnected"
  ├── Enable connect button
  ├── Set button text to "Connect Voice/Chat"
  └── Disable disconnect button
         ↓
Play Sound:
  └── sound_disconnected()
         ↓
Restart Background:
  └── start_background_receiver()
```

### What Happens on Other Side
When peer receives `__DISCONNECT__`:

```
Event: receive_msg_update("__DISCONNECT__")
         ↓
Update UI:
  └── Add system message "📴 Friend disconnected"
         ↓
Play Sound:
  └── sound_disconnected()
         ↓
Auto Disconnect:
  └── disconnect() called if is_connected
```

---

## Message Protocol

### Control Messages

| Message | Direction | Purpose |
|---------|-----------|---------|
| `__CALL_REQUEST__` | Caller → Callee | Initiate call |
| `__CALL_ACCEPT__` | Callee → Caller | Accept incoming call |
| `__CALL_REJECT__` | Callee → Caller | Reject incoming call |
| `__CALL_CANCEL__` | Caller → Callee | Cancel outgoing call |
| `__DISCONNECT__` | Either → Either | End active call |

All control messages are sent using `send_text_message(message, target_ip)`.

---

## UI Components

### Sidebar Elements
| Component | Variable | Purpose |
|-----------|----------|---------|
| Contacts Dropdown | `contacts_dropdown` | Select call target |
| Connect Button | `connect_btn` | Initiate call |
| Disconnect Button | `disconnect_btn` | End call |
| Mute Switch | `mute_switch` | Mute microphone |
| Deafen Switch | `deafen_switch` | Mute speakers |

### Popups/Dialogs
| Popup | Variable | Trigger |
|-------|----------|---------|
| Calling Popup | `calling_popup` | User initiates call |
| Incoming Call Popup | `incoming_call_popup` | Receives call request |

### Button States During Call

| State | Connect Button | Disconnect Button |
|-------|----------------|-------------------|
| Idle | Enabled, "Connect Voice/Chat" | Disabled |
| Calling | Disabled, "Calling..." | Disabled |
| Ringing | N/A (popup shown) | N/A |
| Connected | Disabled, "Connected!" | Enabled |

---

## Sequence Diagrams

### Successful Call Flow
```
Caller                              Callee
   |                                   |
   |--- Select Contact --------------->|
   |                                   |
   |--- Click Connect --------------->>|
   |                                   |
   |===== __CALL_REQUEST__ ===========>|
   |                                   |
   |    [Shows Calling Popup]     [Shows Incoming Popup]
   |    call_state = "calling"    call_state = "ringing"
   |                              incoming_call_ip = caller
   |                                   |
   |                    Click Accept --|
   |                                   |
   |<========== __CALL_ACCEPT__ =======|
   |                                   |
   |    [Popup Closes]         [Popup Closes]
   |    call_state = "connected" call_state = "connected"
   |    is_connected = True      is_connected = True
   |                                   |
   |<======= Audio Stream ============>|
   |                                   |
   |         CONNECTED                 |
```

### Rejected Call Flow
```
Caller                              Callee
   |                                   |
   |===== __CALL_REQUEST__ ===========>|
   |    call_state = "calling"    call_state = "ringing"
   |                                   |
   |                    Click Reject --|
   |                                   |
   |<========== __CALL_REJECT__ =======|
   |                                   |
   |    call_state = "idle"       call_state = "idle"
   |    target_ip = None          incoming_call_ip = None
   |         IDLE                 IDLE |
```

### Cancelled Call Flow
```
Caller                              Callee
   |                                   |
   |===== __CALL_REQUEST__ ===========>|
   |    call_state = "calling"    call_state = "ringing"
   |                                   |
   |-- Click Cancel                    |
   |                                   |
   |===== __CALL_CANCEL__ ============>|
   |                                   |
   |    call_state = "idle"       call_state = "idle"
   |    target_ip = None          incoming_call_ip = None
   |         IDLE                 IDLE |
```

---

## Sound Effects

| Event | Function | Sound |
|-------|----------|-------|
| Initiating call | `sound_calling()` | Ringing tone |
| Receiving call | `sound_incoming()` | Incoming ringtone |
| Call connected | `sound_connected()` | Connection success |
| Call rejected | `sound_rejected()` | Rejection tone |
| Call cancelled | `sound_cancelled()` | Cancellation tone |
| Disconnected | `sound_disconnected()` | Disconnect tone |
| Text message | `sound_message()` | Message notification |

---

## Error Handling

- **No contact selected**: Shows warning message in chat
- **Already in call**: Prevents duplicate call attempts
- **Connection errors**: Caught and displayed as error messages
- **Audio setup failures**: Logged to console

---

## Known Issues & Code Bugs

> ✅ **All issues below have been fixed as of January 2026**

### 1. ~~`sender_ip` Is Discarded in Message Callback~~ ✅ FIXED

**Location**: [ui_backend_flet.py](../ui_modules/ui_backend_flet.py#L126-L130)

**Fix Applied**: The `msg_callback_with_sender` now passes `sender_ip` to `receive_msg_update()`:

```python
def msg_callback_with_sender(message, sender_ip):
    self.receive_msg_update(message, sender_ip)  # ← sender_ip now passed!
```

---

### 2. ~~Self-Call Logic Is Incomplete~~ ✅ FIXED

**Location**: [ui_backend_flet.py](../ui_modules/ui_backend_flet.py#L261-L320)

**Fix Applied**: Mutual call scenario now auto-accepts immediately:

```python
if self.call_state == "calling" and caller_ip == self.target_ip:
    # Mutual call detected - auto-accept immediately
    stop_all_sounds()
    self._close_all_call_popups()
    self.call_state = "connected"
    # ... setup audio and send __CALL_ACCEPT__
```

---

### 3. ~~No Validation of Control Message Sender~~ ✅ FIXED

**Location**: [ui_backend_flet.py](../ui_modules/ui_backend_flet.py#L578-L680)

**Fix Applied**: All control messages now validate the sender:

```python
elif message == "__CALL_ACCEPT__":
    # Validate sender - must be from the person we're calling
    if sender_ip and self.target_ip and sender_ip != self.target_ip:
        print(f"[SECURITY] Ignoring __CALL_ACCEPT__ from {sender_ip}, expected {self.target_ip}")
        return
```

Same validation added for `__CALL_REJECT__`, `__CALL_CANCEL__`, and `__DISCONNECT__`.

---

### 4. ~~Race Condition: Mutual Calls~~ ✅ FIXED

**Fix Applied**: When both users call each other simultaneously, the first to receive `__CALL_REQUEST__` while in `calling` state will auto-accept, and both transition to `connected` state cleanly.

---

## Message Routing Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                     audio_receiver.py                           │
│                                                                 │
│  Receives UDP packet                                            │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────────┐                                            │
│  │ msg_type check  │                                            │
│  └────────┬────────┘                                            │
│           │                                                     │
│    ┌──────┴──────────────────────────┐                          │
│    │                                 │                          │
│    ▼                                 ▼                          │
│ TEXT_MESSAGE                    AUDIO_DATA                      │
│    │                                 │                          │
│    ▼                                 ▼                          │
│ decrypt_text()                  Play audio                      │
│    │                                                            │
│    ▼                                                            │
│ ┌────────────────────┐                                          │
│ │ Is "__CALL_REQUEST__"? │                                      │
│ └─────────┬──────────┘                                          │
│     YES   │   NO                                                │
│     ▼     ▼                                                     │
│ _incoming_call_callback()    _text_message_callback_with_sender()│
│     │                              │                            │
└─────┼──────────────────────────────┼────────────────────────────┘
      │                              │
      ▼                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ui_backend_flet.py                           │
│                                                                 │
│  show_incoming_call()          receive_msg_update()             │
│  (handles __CALL_REQUEST__)    (handles all other messages)     │
│         │                              │                        │
│         ▼                              ▼                        │
│  Shows incoming popup          Processes:                       │
│  Sets call_state="ringing"     - __CALL_ACCEPT__                │
│                                - __CALL_REJECT__                │
│                                - __CALL_CANCEL__                │
│                                - __DISCONNECT__                 │
│                                - Regular text messages          │
└─────────────────────────────────────────────────────────────────┘
```

---

*Last updated: January 2026*
