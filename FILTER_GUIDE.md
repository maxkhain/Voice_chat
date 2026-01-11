"""
FILTER USAGE GUIDE
==================

This document explains how to use the audio filter system.

AVAILABLE FILTERS:
==================

1. high_pass (default ON)
   - Removes low-frequency rumble and hum below 80Hz
   - Config: HIGH_PASS_CUTOFF (default: 80 Hz)

2. low_pass (default OFF)
   - Removes high-frequency hiss and noise above 8000Hz
   - Config: LOW_PASS_CUTOFF (default: 8000 Hz)

3. noise_gate (default OFF)
   - Mutes frames with volume below threshold
   - Config: NOISE_GATE_THRESHOLD (default: 300 RMS)
           NOISE_GATE_ATTACK (default: 0.01s)
           NOISE_GATE_RELEASE (default: 0.1s)

4. spectral_subtraction (default OFF)
   - Learns noise profile from quiet audio, then subtracts it
   - Config: SPECTRAL_SUBTRACT_ALPHA (default: 0.5, range 0-1)
           NOISE_LEARNING_FRAMES (default: 30 frames)

5. compressor (default OFF)
   - Reduces dynamic range above threshold for more consistent volume
   - Config: COMPRESSOR_THRESHOLD (default: 2000 RMS)
           COMPRESSOR_RATIO (default: 4.0, e.g., 4:1 compression)
           COMPRESSOR_ATTACK (default: 0.005s)
           COMPRESSOR_RELEASE (default: 0.05s)

6. limiter (default OFF)
   - Hard ceiling to prevent clipping and distortion
   - Config: LIMITER_THRESHOLD (default: 28000 peak)
           LIMITER_RELEASE (default: 0.03s)

7. eq_3band (default OFF)
   - 3-band equalizer to boost/cut low, mid, high frequencies
   - Low band: <300Hz
   - Mid band: 300-3000Hz
   - High band: >3000Hz
   - Config: EQ_LOW_GAIN (default: 0 dB)
           EQ_MID_GAIN (default: 0 dB)
           EQ_HIGH_GAIN (default: 0 dB)
   - Example: EQ_LOW_GAIN = -6 (cut lows by 6dB)
            EQ_HIGH_GAIN = 3 (boost highs by 3dB)

8. notch (default OFF)
   - Removes specific frequency (e.g., 60Hz AC hum or 50Hz European power hum)
   - Config: NOTCH_FREQUENCY (default: 60 Hz)
           NOTCH_Q (default: 10, higher = narrower notch)

9. gain (default OFF)
   - Amplify or reduce overall signal level
   - Config: GAIN_DB (default: 0 dB)
   - Example: GAIN_DB = 6 (amplify by 6dB, ~2x louder)
             GAIN_DB = -3 (reduce by 3dB, ~0.7x quieter)


HOW TO USE:
===========

1. ENABLE/DISABLE FILTERS:

   Option A: Edit audio_config.py
   ---------
   FILTER_ENABLED = {
       'high_pass': True,           # ON
       'low_pass': False,           # OFF
       'noise_gate': True,          # ON
       'spectral_subtraction': False,
       ...
   }

   Option B: Use functions in your code
   --------
   from audio_filter import toggle_filter, print_filter_status
   
   toggle_filter('compressor')      # Toggle compressor on/off
   print_filter_status()             # See current status


2. ADJUST PARAMETERS:

   Edit audio_config.py:
   ---------------------
   
   # Example: Strengthen high-pass filter
   HIGH_PASS_CUTOFF = 200  # Default was 80 Hz
   
   # Example: Add compression
   COMPRESSOR_THRESHOLD = 1500
   COMPRESSOR_RATIO = 6.0
   
   # Example: Boost treble and cut bass with EQ
   EQ_LOW_GAIN = -3       # Cut lows by 3dB
   EQ_HIGH_GAIN = 6       # Boost highs by 6dB


3. FILTER ORDER:

   Filters are always applied in this optimal order:
   1. noise_gate (remove silence first)
   2. spectral_subtraction (remove background noise)
   3. high_pass (remove rumble)
   4. low_pass (remove hiss)
   5. notch (remove hum)
   6. eq_3band (shape tone)
   7. compressor (level control)
   8. limiter (prevent clipping)
   9. gain (final amplification)


COMMON CONFIGURATIONS:
======================

CLEAN SPEECH (minimize processing):
  high_pass: True (removes rumble)
  All others: False

NOISY ENVIRONMENT:
  high_pass: True
  low_pass: True          (remove high-freq hiss)
  noise_gate: True        (remove silence/gaps)
  spectral_subtraction: True
  notch: True (if 60Hz hum present)

BROADCAST QUALITY:
  high_pass: True
  notch: True
  eq_3band: True          (shape tone)
  compressor: True        (consistent volume)
  limiter: True           (safety against clipping)
  gain: True              (final level adjustment)

BALANCED (good for most uses):
  high_pass: True
  noise_gate: False
  spectral_subtraction: False
  compressor: True        (gentle, ratio=2-3)
  limiter: True
  gain: False

MAXIMUM NOISE REDUCTION:
  high_pass: True
  low_pass: True
  noise_gate: True
  spectral_subtraction: True
  notch: True
  compressor: True (aggressive, ratio=8+)
  limiter: True
  gain: True (as needed)


TESTING & TUNING:
=================

1. Start with one filter at a time
2. Adjust parameters gradually (in small steps)
3. Listen to the effect
4. Build up complexity by enabling more filters

Example workflow:
  Step 1: Enable high_pass only
  Step 2: Add noise_gate, tune threshold
  Step 3: Add compressor, adjust ratio
  Step 4: Add limiter for safety
  Step 5: Add EQ to shape tone if needed

Use print_filter_status() to see active filters anytime.


IMPORTANT NOTES:
================

- Filter processing happens in real-time but adds latency (typically <50ms)
- Too many filters = more CPU usage and potential artifacts
- Filters process OUTGOING audio (what you send)
- Less aggressive is usually better (quality over quantity)
- Test with actual conversation, not just silence
- Different microphones may need different settings
- Environment noise varies (use spectral_subtraction in noisy spaces)
"""
