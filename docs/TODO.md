# TODO List - Local Voice Chat

## 🔴 CRITICAL BUGS TO FIX

### Duplicate Files (MUST FIX IMMEDIATELY)
- [ ] **Delete root `ui.py`** - Old version with wrong imports exists alongside new `ui_modules/ui.py`
- [ ] **Delete root `sounds/` folder** - Duplicated in `audio_modules/sounds/`
- [ ] **Delete `config/contacts.json`** - Should only exist in root as `contacts.json`
- [ ] **Delete `config/.chat_history.json`** - Should only exist in root
- [ ] **Delete `config/.chat_backups/`** - Should only exist in root
- [ ] **Delete `utils/.connection_cache.json`** - Should only exist in root
- [ ] **Delete `utils/.scan_cache.json`** - Should only exist in root

### Sound Effects Issues
- [ ] **Sound files not found by receiver** - When receiving `__SOUND__` messages, the path resolution fails
  - Root cause: Possible cached import or wrong SOUNDS_DIR path at runtime
  - Need to verify `audio_modules/sounds/` contains all sound files
  - Check if receiver is using correct module imports

### Import Path Issues
- [ ] Ensure all Python files use proper module imports (audio_modules.*, config.*, utils.*)
- [ ] Clean up `__pycache__` folders that may have stale compiled imports

## 🟡 Features to Implement

### High Priority
- [ ] Contact List & Friends
  - ✅ Save device IPs with custom names (DONE)
  - ✅ Maintain friends list file (DONE)
  - [ ] Edit/delete contacts
  - [ ] Import/export contacts
  - [ ] Mark favorites

- [ ] Multiple Device Support
  - [ ] Connect to multiple devices simultaneously
  - [ ] Chat with multiple contacts at same time
  - [ ] Switch between active conversations
  - ✅ Tab or side panel for each conversation (DONE)
  - [ ] Display active connection count

- [ ] Auto-accept calls when both sides initiate
  - [ ] Detect simultaneous call requests
  - [ ] Automatically establish connection
  - [ ] Notify user of automatic acceptance
  - [ ] Option to disable auto-accept

- [x] Add sound effects (DONE)
  - ✅ Message received sound
  - ✅ Connection/disconnect sounds
  - ✅ Fun reaction sounds (squeaky, boing, drums, laughs, trombones)
  - ✅ Configurable volume per category
  - [ ] Fix sound playback on receiver side

- [ ] IP Scan
  - ✅ Basic ICMP ping scanning (DONE)
  - [ ] Add ARP scanning for devices blocking ICMP
  - ✅ Cache discovered devices (DONE)
  - [ ] Custom network range selection
  - [ ] Scan progress indicator in UI

- [ ] Save Chat History Locally
  - ✅ Store messages with timestamps (DONE)
  - ✅ Consolidated into single file (DONE)
  - ✅ Load history on reconnect (DONE)
  - ✅ Auto-load chat on app startup (DONE)
  - ✅ Enable chat without calling (DONE)
  - ✅ Save messages even without voice call (DONE)
  - [ ] Export chat as text/JSON
  - [ ] Search chat history
  - [ ] Clear history option (per contact)

### Medium Priority
- [ ] GIFs to Chat
  - [ ] GIF search integration (Giphy API)
  - [ ] GIF picker window
  - [ ] Embed GIFs in messages
  - [ ] GIF history/favorites
  - [ ] Drag & drop GIF support

- [ ] Emoji Panel Improvements
  - ✅ Basic emoji panel (DONE)
  - [ ] More emoji categories
  - [ ] Recently used emojis
  - [ ] Emoji search

### Low Priority
- [ ] Additional UI Enhancements
  - [ ] User avatar/profile
  - ✅ Message timestamps (DONE)
  - [ ] Read receipts
  - [ ] Typing indicators
  - [ ] Message search
  - [ ] Auto size window
  - ✅ Dark theme (DONE)

- [ ] Performance Optimizations
  - [ ] Reduce audio latency
  - [ ] Better audio codec selection
  - [ ] Network bandwidth optimization

- [ ] Security Enhancements
  - ✅ AES-256 Encryption (DONE)
  - [ ] Custom encryption keys per contact
  - [ ] Key exchange protocol
  - [ ] Message signing
  - [ ] Audit logging

## ✅ Completed Features
- [x] P2P Voice Communication
- [x] Text Chat Messaging
- [x] Audio Filtering & Noise Cancellation
- [x] Device Selection (Mic/Speaker)
- [x] Mute/Deafen Controls
- [x] Auto-save Connection Settings
- [x] AES-256 Encryption
- [x] Network Scanner (ICMP)
- [x] Optimized Multi-threaded Scan
- [x] Consolidated Chat History (Single File)
- [x] Chat Without Calling (Text-only Mode)
- [x] Select From Scan List to Message or Call
- [x] Contacts System with Names
- [x] Call Accept/Reject/Cancel with Popups
- [x] Sound Effects (call sounds, message sounds)
- [x] Fun Reaction Sounds (sender side working)
- [x] Volume Controls in Settings
- [x] Emoji Panel
- [x] Date Separators in Chat
- [x] Tabbed Chat Interface
- [x] Code Reorganization into Modules
- [x] Desktop Shortcut Generator
- [x] Dark Theme

## 🔧 Code Cleanup Needed
- [ ] Remove duplicate files (see Critical Bugs)
- [ ] Update all documentation to match actual structure
- [ ] Clean __pycache__ folders
- [ ] Add proper docstrings to all functions
- [ ] Create unit tests for core functionality
- [ ] Add type hints throughout codebase

## Notes
- Network scanner needs ARP support for devices blocking ICMP
- GIF integration requires API key (Giphy/Tenor)
- Contact list uses local JSON file
- Sound files must be in `audio_modules/sounds/` for proper detection

---
**Last Updated**: January 15, 2026
**Status**: Active Development
