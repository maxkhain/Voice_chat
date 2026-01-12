# TODO List - Local Voice Chat

## Features to Implement

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
  - [ ] Tab or side panel for each conversation
  - [ ] Display active connection count

- [ ] Auto-accept calls when both sides initiate
  - Detect simultaneous call requests
  - Automatically establish connection
  - Notify user of automatic acceptance
  - Option to disable auto-accept

- [ ] Add sound effects
  - Message received sound
  - Connection/disconnect sounds
  - Alert sounds
  - Configurable volume

- [ ] IP Scan
  - ✅ Basic ICMP ping scanning (DONE)
  - [ ] Add ARP scanning for devices blocking ICMP
  - [ ] Cache discovered devices
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
  - [ ] Clear history option

### Medium Priority
- [ ] GIFs to Chat
  - GIF search integration (Giphy API)
  - GIF picker window
  - Embed GIFs in messages
  - GIF history/favorites
  - Drag & drop GIF support

### Low Priority
- [ ] Additional UI Enhancements
  - User avatar/profile
  - Message timestamps
  - Read receipts
  - Typing indicators
  - Message search

- [ ] Performance Optimizations
  - Reduce latency
  - Better audio codec selection
  - Network bandwidth optimization

- [ ] Security Enhancements
  - Custom encryption keys per contact
  - Key exchange protocol
  - Message signing
  - Audit logging

## Completed Features ✅
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

## Notes
- Network scanner needs ARP support for devices blocking ICMP
- Consider adding notification sounds when new message arrives
- GIF integration requires API key (Giphy/Tenor)
- Contact list should use local JSON database

---
**Last Updated**: January 12, 2026
**Status**: Active Development
