"""
Audio filtering: comprehensive suite of audio filters with independent enable/disable.

Available filters:
  - High-pass filter (remove low-freq rumble)
  - Low-pass filter (remove high-freq hiss)
  - Noise gate (mute quiet frames)
  - Spectral subtraction (subtract learned noise)
  - Compressor (compress dynamic range)
  - Limiter (prevent clipping)
  - 3-band EQ (boost/cut low, mid, high)
  - Notch filter (remove specific frequency like hum)
  - Gain (amplify/reduce signal)

Use FILTER_ENABLED dict to toggle filters on/off individually.
"""
import numpy as np
from audio_config import (
    RATE,
    CHUNK,
    FILTER_ENABLED,
    # High-pass
    HIGH_PASS_CUTOFF,
    # Low-pass
    LOW_PASS_CUTOFF,
    # Noise gate
    NOISE_GATE_THRESHOLD,
    NOISE_GATE_ATTACK,
    NOISE_GATE_RELEASE,
    # Spectral subtraction
    SPECTRAL_SUBTRACT_ALPHA,
    NOISE_LEARNING_FRAMES,
    # Compressor
    COMPRESSOR_THRESHOLD,
    COMPRESSOR_RATIO,
    COMPRESSOR_ATTACK,
    COMPRESSOR_RELEASE,
    # Limiter
    LIMITER_THRESHOLD,
    LIMITER_RELEASE,
    # EQ
    EQ_LOW_GAIN,
    EQ_MID_GAIN,
    EQ_HIGH_GAIN,
    # Notch
    NOTCH_FREQUENCY,
    NOTCH_Q,
    # Gain
    GAIN_DB,
)

# ============================================================================
# GLOBAL STATE FOR FILTERS
# ============================================================================

# Spectral subtraction state
_NOISE_PROFILE = None
_LEARNING_FRAME_COUNT = 0

# High-pass filter state (IIR)
_HP_FILTER_STATE = 0.0

# Low-pass filter state (IIR)
_LP_FILTER_STATE = 0.0

# Noise gate state
_GATE_ENVELOPE = 0.0

# Compressor state
_COMPRESSOR_ENVELOPE = 0.0

# Notch filter state
_NOTCH_FILTER_STATE_1 = 0.0
_NOTCH_FILTER_STATE_2 = 0.0


# ============================================================================
# INDIVIDUAL FILTER FUNCTIONS
# ============================================================================

def apply_high_pass_filter(audio_bytes):
    """
    First-order IIR high-pass filter to remove low-frequency rumble/hum.
    """
    global _HP_FILTER_STATE
    try:
        samples = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
        cutoff_norm = HIGH_PASS_CUTOFF / RATE
        alpha = cutoff_norm / (cutoff_norm + 1)
        
        filtered = np.zeros_like(samples)
        for i in range(len(samples)):
            if i == 0:
                filtered[i] = alpha * samples[i]
            else:
                filtered[i] = alpha * (filtered[i-1] + samples[i] - samples[i-1])
        
        filtered = np.clip(filtered, -32768, 32767).astype(np.int16)
        return filtered.tobytes()
    except Exception:
        return audio_bytes


def apply_low_pass_filter(audio_bytes):
    """
    First-order IIR low-pass filter to remove high-frequency hiss and noise.
    """
    global _LP_FILTER_STATE
    try:
        samples = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
        cutoff_norm = LOW_PASS_CUTOFF / RATE
        alpha = cutoff_norm / (cutoff_norm + 1)
        
        filtered = np.zeros_like(samples)
        for i in range(len(samples)):
            filtered[i] = alpha * samples[i] + (1 - alpha) * (filtered[i-1] if i > 0 else samples[i])
        
        filtered = np.clip(filtered, -32768, 32767).astype(np.int16)
        return filtered.tobytes()
    except Exception:
        return audio_bytes


def apply_noise_gate(audio_bytes):
    """
    Mute frames with RMS below threshold (noise gate).
    """
    global _GATE_ENVELOPE
    try:
        samples = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
        rms = np.sqrt(np.mean(samples ** 2))
        
        # Envelope follower with attack and release
        attack_coeff = 1 - np.exp(-2.0 / (NOISE_GATE_ATTACK * RATE))
        release_coeff = 1 - np.exp(-2.0 / (NOISE_GATE_RELEASE * RATE))
        
        if rms > _GATE_ENVELOPE:
            _GATE_ENVELOPE += attack_coeff * (rms - _GATE_ENVELOPE)
        else:
            _GATE_ENVELOPE += release_coeff * (rms - _GATE_ENVELOPE)
        
        if _GATE_ENVELOPE < NOISE_GATE_THRESHOLD:
            return np.zeros(len(samples), dtype=np.int16).tobytes()
        
        return audio_bytes
    except Exception:
        return audio_bytes



def apply_spectral_subtraction(audio_bytes):
    """
    Subtract learned noise profile from audio spectrum.
    Learns from quiet frames, then subtracts noise continuously.
    """
    global _NOISE_PROFILE, _LEARNING_FRAME_COUNT
    try:
        samples = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
        rms = np.sqrt(np.mean(samples ** 2))
        
        # Learning phase: build noise profile from quiet frames
        if _LEARNING_FRAME_COUNT < NOISE_LEARNING_FRAMES and rms < NOISE_GATE_THRESHOLD:
            _LEARNING_FRAME_COUNT += 1
            fft = np.abs(np.fft.rfft(samples))
            if _NOISE_PROFILE is None:
                _NOISE_PROFILE = fft.copy()
            else:
                _NOISE_PROFILE = 0.9 * _NOISE_PROFILE + 0.1 * fft
            return audio_bytes
        
        # Application phase: subtract noise from spectrum
        if _NOISE_PROFILE is not None and len(_NOISE_PROFILE) > 0:
            fft = np.fft.rfft(samples)
            mag = np.abs(fft)
            phase = np.angle(fft)
            
            # Subtract noise; prevent over-subtraction
            mag_reduced = mag - SPECTRAL_SUBTRACT_ALPHA * _NOISE_PROFILE[:len(mag)]
            mag_reduced = np.maximum(mag_reduced, 0.05 * mag)
            
            fft_new = mag_reduced * np.exp(1j * phase)
            samples = np.fft.irfft(fft_new, n=len(samples))
            samples = np.clip(samples, -32768, 32767).astype(np.int16)
            return samples.tobytes()
        
        return audio_bytes
    except Exception:
        return audio_bytes


def apply_compressor(audio_bytes):
    """
    Dynamic range compressor to reduce loud peaks and boost quiet signals.
    Reduces dynamic range above threshold with configurable ratio.
    """
    global _COMPRESSOR_ENVELOPE
    try:
        samples = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
        rms = np.sqrt(np.mean(samples ** 2))
        
        # Envelope follower
        attack_coeff = 1 - np.exp(-2.0 / (COMPRESSOR_ATTACK * RATE))
        release_coeff = 1 - np.exp(-2.0 / (COMPRESSOR_RELEASE * RATE))
        
        if rms > _COMPRESSOR_ENVELOPE:
            _COMPRESSOR_ENVELOPE += attack_coeff * (rms - _COMPRESSOR_ENVELOPE)
        else:
            _COMPRESSOR_ENVELOPE += release_coeff * (rms - _COMPRESSOR_ENVELOPE)
        
        # Calculate gain reduction
        if _COMPRESSOR_ENVELOPE > COMPRESSOR_THRESHOLD:
            excess = _COMPRESSOR_ENVELOPE - COMPRESSOR_THRESHOLD
            gain_reduction = 1.0 / (1.0 + (COMPRESSOR_RATIO - 1.0) * (excess / COMPRESSOR_THRESHOLD))
        else:
            gain_reduction = 1.0
        
        samples = samples * gain_reduction
        samples = np.clip(samples, -32768, 32767).astype(np.int16)
        return samples.tobytes()
    except Exception:
        return audio_bytes


def apply_limiter(audio_bytes):
    """
    Hard limiter to prevent clipping and distortion above threshold.
    """
    try:
        samples = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
        
        # Peak detection
        max_sample = np.max(np.abs(samples))
        
        # If we're above threshold, reduce all samples proportionally
        if max_sample > LIMITER_THRESHOLD:
            gain = LIMITER_THRESHOLD / max_sample
            samples = samples * gain
        
        samples = np.clip(samples, -32768, 32767).astype(np.int16)
        return samples.tobytes()
    except Exception:
        return audio_bytes


def apply_3band_eq(audio_bytes):
    """
    Simple 3-band equalizer: boost/cut low, mid, and high frequencies.
    Uses basic shelving filters.
    """
    try:
        samples = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
        
        # Apply low-shelf boost/cut (below 300Hz)
        if EQ_LOW_GAIN != 0.0:
            low_gain = 10 ** (EQ_LOW_GAIN / 20.0)  # Convert dB to linear
            samples = apply_simple_low_shelf(samples, 300, low_gain)
        
        # Apply high-shelf boost/cut (above 3000Hz)
        if EQ_HIGH_GAIN != 0.0:
            high_gain = 10 ** (EQ_HIGH_GAIN / 20.0)
            samples = apply_simple_high_shelf(samples, 3000, high_gain)
        
        # Mid gain is implicit (if both low and high are boosted, mids are cut relatively)
        if EQ_MID_GAIN != 0.0:
            mid_gain = 10 ** (EQ_MID_GAIN / 20.0)
            samples = samples * mid_gain
        
        samples = np.clip(samples, -32768, 32767).astype(np.int16)
        return samples.tobytes()
    except Exception:
        return audio_bytes


def apply_simple_low_shelf(samples, shelf_freq, gain):
    """Simple low-shelf filter approximation."""
    cutoff_norm = shelf_freq / RATE
    alpha = cutoff_norm / (cutoff_norm + 1)
    
    # Blend between original and low-pass filtered
    filtered = apply_simple_lowpass_array(samples, alpha)
    return samples * (1 - gain) + filtered * gain


def apply_simple_high_shelf(samples, shelf_freq, gain):
    """Simple high-shelf filter approximation."""
    cutoff_norm = shelf_freq / RATE
    alpha = cutoff_norm / (cutoff_norm + 1)
    
    # Blend between original and high-pass filtered
    filtered = apply_simple_highpass_array(samples, alpha)
    return samples * (1 - gain) + filtered * gain


def apply_simple_lowpass_array(samples, alpha):
    """Apply low-pass to array."""
    filtered = np.zeros_like(samples)
    for i in range(len(samples)):
        filtered[i] = alpha * samples[i] + (1 - alpha) * (filtered[i-1] if i > 0 else samples[i])
    return filtered


def apply_simple_highpass_array(samples, alpha):
    """Apply high-pass to array."""
    filtered = np.zeros_like(samples)
    for i in range(len(samples)):
        if i == 0:
            filtered[i] = alpha * samples[i]
        else:
            filtered[i] = alpha * (filtered[i-1] + samples[i] - samples[i-1])
    return filtered


def apply_notch_filter(audio_bytes):
    """
    Notch filter to remove specific frequency (e.g., 60Hz hum).
    Uses a simple second-order IIR notch design.
    """
    global _NOTCH_FILTER_STATE_1, _NOTCH_FILTER_STATE_2
    try:
        samples = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
        
        # Normalized frequency
        w0 = 2 * np.pi * NOTCH_FREQUENCY / RATE
        sin_w0 = np.sin(w0)
        cos_w0 = np.cos(w0)
        alpha = sin_w0 / (2 * NOTCH_Q)
        
        # Notch filter coefficients
        b0 = 1
        b1 = -2 * cos_w0
        b2 = 1
        a0 = 1 + alpha
        a1 = -2 * cos_w0
        a2 = 1 - alpha
        
        # Normalize
        b0 /= a0
        b1 /= a0
        b2 /= a0
        a1 /= a0
        a2 /= a0
        
        # Apply filter
        filtered = np.zeros_like(samples)
        state_1 = 0.0
        state_2 = 0.0
        
        for i in range(len(samples)):
            output = b0 * samples[i] + state_1
            state_1 = b1 * samples[i] - a1 * output + state_2
            state_2 = b2 * samples[i] - a2 * output
            filtered[i] = output
        
        filtered = np.clip(filtered, -32768, 32767).astype(np.int16)
        return filtered.tobytes()
    except Exception:
        return audio_bytes


def apply_gain(audio_bytes):
    """
    Apply gain (amplification or reduction) to the audio signal.
    Positive dB = amplify, negative dB = reduce.
    """
    try:
        samples = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
        gain_linear = 10 ** (GAIN_DB / 20.0)  # Convert dB to linear
        samples = samples * gain_linear
        samples = np.clip(samples, -32768, 32767).astype(np.int16)
        return samples.tobytes()
    except Exception:
        return audio_bytes


# ============================================================================
# MAIN FILTER ORCHESTRATION
# ============================================================================

def apply_all_enabled_filters(audio_bytes):
    """
    Apply all enabled filters in optimal order.
    Order matters for audio quality!
    """
    # Order: gates -> spectral -> high/low pass -> eq -> compressor -> limiter -> gain
    
    # 1. Noise gate (remove silence first)
    if FILTER_ENABLED.get('noise_gate', False):
        audio_bytes = apply_noise_gate(audio_bytes)
    
    # 2. Spectral subtraction (remove background noise)
    if FILTER_ENABLED.get('spectral_subtraction', False):
        audio_bytes = apply_spectral_subtraction(audio_bytes)
    
    # 3. High-pass filter (remove rumble)
    if FILTER_ENABLED.get('high_pass', False):
        audio_bytes = apply_high_pass_filter(audio_bytes)
    
    # 4. Low-pass filter (remove hiss)
    if FILTER_ENABLED.get('low_pass', False):
        audio_bytes = apply_low_pass_filter(audio_bytes)
    
    # 5. Notch filter (remove hum)
    if FILTER_ENABLED.get('notch', False):
        audio_bytes = apply_notch_filter(audio_bytes)
    
    # 6. EQ (shape tone)
    if FILTER_ENABLED.get('eq_3band', False):
        audio_bytes = apply_3band_eq(audio_bytes)
    
    # 7. Compressor (level control)
    if FILTER_ENABLED.get('compressor', False):
        audio_bytes = apply_compressor(audio_bytes)
    
    # 8. Limiter (prevent clipping)
    if FILTER_ENABLED.get('limiter', False):
        audio_bytes = apply_limiter(audio_bytes)
    
    # 9. Gain (final amplification)
    if FILTER_ENABLED.get('gain', False):
        audio_bytes = apply_gain(audio_bytes)
    
    return audio_bytes


def reset_all_filters():
    """Reset all filter states for a fresh session."""
    global _NOISE_PROFILE, _LEARNING_FRAME_COUNT, _HP_FILTER_STATE, _LP_FILTER_STATE
    global _GATE_ENVELOPE, _COMPRESSOR_ENVELOPE, _NOTCH_FILTER_STATE_1, _NOTCH_FILTER_STATE_2
    
    _NOISE_PROFILE = None
    _LEARNING_FRAME_COUNT = 0
    _HP_FILTER_STATE = 0.0
    _LP_FILTER_STATE = 0.0
    _GATE_ENVELOPE = 0.0
    _COMPRESSOR_ENVELOPE = 0.0
    _NOTCH_FILTER_STATE_1 = 0.0
    _NOTCH_FILTER_STATE_2 = 0.0


def get_active_filters():
    """Return list of currently enabled filters."""
    return [name for name, enabled in FILTER_ENABLED.items() if enabled]


def toggle_filter(filter_name):
    """Toggle a specific filter on/off."""
    if filter_name in FILTER_ENABLED:
        FILTER_ENABLED[filter_name] = not FILTER_ENABLED[filter_name]
        status = "ON" if FILTER_ENABLED[filter_name] else "OFF"
        print(f"✓ Filter '{filter_name}' is now {status}")
    else:
        print(f"✗ Unknown filter: {filter_name}")


def print_filter_status():
    """Print current status of all filters."""
    print("\n=== Active Filters ===")
    for name, enabled in FILTER_ENABLED.items():
        status = "✓" if enabled else "✗"
        print(f"  {status} {name}")
    print()


# Legacy support - apply_noise_cancellation() calls new system
def apply_noise_cancellation(audio_bytes):
    """
    Legacy function for backward compatibility.
    Now delegates to new filter system.
    """
    return apply_all_enabled_filters(audio_bytes)


# Legacy support
def reset_noise_profile():
    """Legacy function for backward compatibility."""
    reset_all_filters()
