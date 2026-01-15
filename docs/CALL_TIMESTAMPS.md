# Call Timestamps - Implementation Complete

## What Was Fixed

All call-related system messages now include timestamps, just like regular chat messages.

## Changes Made

### Before
```
[21:30:24] You: a
[21:30:26] You: aa

[CALLING] 192.168.1.185...
--- Connected to 192.168.1.185 ---

[22:42:20] You: a
```

### After
```
[21:30:24] You: a
[21:30:26] You: aa

[15:45:30] 📞 CALLING 192.168.1.185...
[15:45:35] ✅ Connected to 192.168.1.185

[22:42:20] You: a
```

## System Messages with Timestamps

All these events now display with time stamps (HH:MM:SS format):

1. **📞 CALLING** - When you initiate a call
   ```
   [14:30:45] 📞 CALLING 192.168.1.185...
   ```

2. **✅ Connected** - When call is accepted
   ```
   [14:30:52] ✅ Connected to 192.168.1.185
   ```

3. **❌ Call rejected** - When friend rejects your call
   ```
   [14:31:10] ❌ Call rejected
   ```

4. **❌ Call cancelled by friend** - When friend cancels incoming call
   ```
   [14:31:15] ❌ Call cancelled by friend
   ```

5. **📴 Friend disconnected** - When friend disconnects
   ```
   [14:32:00] 📴 Friend disconnected
   ```

6. **📴 Disconnected** - When you disconnect
   ```
   [14:32:05] 📴 Disconnected
   ```

7. **📞 Incoming call** - When receiving an incoming call
   ```
   [14:35:20] 📞 Incoming call from 192.168.1.185
   ```

## Benefits

✅ Complete conversation timeline - Know exactly when calls happened
✅ Better organization - Call events are sorted with messages by time
✅ Professional appearance - Matches WhatsApp/Discord style
✅ Easier tracking - See call durations and gaps between calls
✅ Complete history - All events in chronological order

## Files Modified

- [ui.py](ui.py) - Added timestamps to all 7 call-related system messages

## Testing

All syntax has been validated. The implementation:
- ✅ Uses the same timestamp format as regular messages
- ✅ Works with date separators
- ✅ Preserves all call handling logic
- ✅ No impact on performance
