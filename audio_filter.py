"""
Audio filtering: noise cancellation, noise gate, high-pass filter, and spectral subtraction.
"""
import numpy as np
from audio_config import (
    NOISE_GATE_THRESHOLD,
    HIGH_PASS_CUTOFF,
    SPECTRAL_SUBTRACT_ALPHA,
    NOISE_LEARNING_FRAMES,
    ENABLE_NOISE_CANCELLATION,
    ENABLE_HIGH_PASS_ONLY,
    RATE
)

# Noise cancellation state
_NOISE_PROFILE = None           # Spectral noise signature
_LEARNING_FRAME_COUNT = 0       # Count frames for noise learning
_HP_FILTER_STATE = 0.0          # High-pass filter state (IIR)


def apply_high_pass_filter(audio_bytes):
    """Simple first-order IIR high-pass filter to remove low-freq hum/rumble."""
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
        # If filter fails, return original audio
        return audio_bytes


def apply_spectral_subtraction(audio_bytes):
    """Subtract learned noise profile from audio spectrum."""
    global _NOISE_PROFILE, _LEARNING_FRAME_COUNT
    try:
        samples = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
        rms = np.sqrt(np.mean(samples ** 2))
        
        # During learning phase: build noise profile from quiet frames
        if _LEARNING_FRAME_COUNT < NOISE_LEARNING_FRAMES and rms < NOISE_GATE_THRESHOLD:
            _LEARNING_FRAME_COUNT += 1
            fft = np.abs(np.fft.rfft(samples))
            if _NOISE_PROFILE is None:
                _NOISE_PROFILE = fft.copy()
            else:
                _NOISE_PROFILE = 0.9 * _NOISE_PROFILE + 0.1 * fft
            return audio_bytes  # Return unprocessed during learning
        
        # After learning: apply spectral subtraction
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


def apply_noise_gate(audio_bytes):
    """Mute frames with RMS below threshold."""
    try:
        samples = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
        rms = np.sqrt(np.mean(samples ** 2))
        
        if rms < NOISE_GATE_THRESHOLD:
            return np.zeros(len(samples), dtype=np.int16).tobytes()
        return audio_bytes
    except Exception:
        return audio_bytes


def apply_noise_cancellation(audio_bytes):
    """Apply noise cancellation (disabled for smooth audio by default)."""
    if ENABLE_HIGH_PASS_ONLY:
        # Only apply high-pass filter (no phase artifacts)
        return apply_high_pass_filter(audio_bytes)
    elif ENABLE_NOISE_CANCELLATION:
        # Full noise cancellation suite
        try:
            audio_bytes = apply_high_pass_filter(audio_bytes)
            audio_bytes = apply_spectral_subtraction(audio_bytes)
            audio_bytes = apply_noise_gate(audio_bytes)
            return audio_bytes
        except Exception:
            return audio_bytes
    else:
        # No processing - clean, natural audio
        return audio_bytes


def reset_noise_profile():
    """Reset noise cancellation state."""
    global _NOISE_PROFILE, _LEARNING_FRAME_COUNT, _HP_FILTER_STATE
    _NOISE_PROFILE = None
    _LEARNING_FRAME_COUNT = 0
    _HP_FILTER_STATE = 0.0
