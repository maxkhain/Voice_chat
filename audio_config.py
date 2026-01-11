"""
Audio configuration constants and settings.
"""
import pyaudio

# --- AUDIO STREAM SETTINGS ---
CHUNK = 256             # ~8ms at 16kHz
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
PORT = 6000

# --- NOISE CANCELLATION CONFIG ---
NOISE_GATE_THRESHOLD = 300      # RMS threshold below which audio is muted (lowered from 500)
HIGH_PASS_CUTOFF = 80           # Hz; removes hum/rumble below this
SPECTRAL_SUBTRACT_ALPHA = 0.5   # 0.0-1.0; how much to subtract noise (lowered from 0.8)
NOISE_LEARNING_FRAMES = 30      # Learn noise profile from first N frames of silence
ENABLE_NOISE_CANCELLATION = False  # Keep disabled for smooth audio
ENABLE_HIGH_PASS_ONLY = False     # Enable ONLY high-pass filter (no phase artifacts)

# --- UI SETTINGS ---
VISUAL_THROTTLE = 0.1  # Update frequency for visual indicators (seconds)

# --- SOCKET CONFIG ---
SOCKET_RECV_BUFFER = 256  # Ultra-minimal buffer to prevent accumulation
SOCKET_SEND_BUFFER = 256  # Ultra-minimal buffer to prevent accumulation
