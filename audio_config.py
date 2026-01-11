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

# --- FILTER ENABLE/DISABLE (independently toggleable) ---
FILTER_ENABLED = {
    'high_pass': True,           # Remove low-frequency rumble/hum
    'low_pass': False,           # Remove high-frequency noise
    'noise_gate': False,         # Mute quiet frames below threshold
    'spectral_subtraction': False,  # Subtract learned noise from spectrum
    'compressor': False,         # Compress dynamic range
    'limiter': False,            # Prevent clipping/distortion
    'eq_3band': False,           # 3-band equalizer (low, mid, high)
    'notch': False,              # Remove specific frequency (e.g., 60Hz hum)
    'gain': False,               # Amplify or reduce signal level
}

# --- HIGH-PASS FILTER CONFIG ---
HIGH_PASS_CUTOFF = 80           # Hz; removes hum/rumble below this

# --- LOW-PASS FILTER CONFIG ---
LOW_PASS_CUTOFF = 8000          # Hz; removes high-frequency hiss above this

# --- NOISE GATE CONFIG ---
NOISE_GATE_THRESHOLD = 300      # RMS threshold below which audio is muted
NOISE_GATE_ATTACK = 0.01        # Attack time in seconds
NOISE_GATE_RELEASE = 0.1        # Release time in seconds

# --- SPECTRAL SUBTRACTION CONFIG ---
SPECTRAL_SUBTRACT_ALPHA = 0.5   # 0.0-1.0; how much to subtract noise
NOISE_LEARNING_FRAMES = 30      # Learn noise profile from first N frames of silence

# --- COMPRESSOR CONFIG ---
COMPRESSOR_THRESHOLD = 2000     # RMS level above which compression starts
COMPRESSOR_RATIO = 4.0          # Compression ratio (e.g., 4:1)
COMPRESSOR_ATTACK = 0.005       # Attack time in seconds
COMPRESSOR_RELEASE = 0.05       # Release time in seconds

# --- LIMITER CONFIG ---
LIMITER_THRESHOLD = 28000       # RMS level at which limiting kicks in
LIMITER_RELEASE = 0.03          # Release time in seconds

# --- 3-BAND EQ CONFIG (low, mid, high) ---
EQ_LOW_GAIN = 0.0               # Gain in dB for low frequencies (<300Hz)
EQ_MID_GAIN = 0.0               # Gain in dB for mid frequencies (300-3000Hz)
EQ_HIGH_GAIN = 0.0              # Gain in dB for high frequencies (>3000Hz)

# --- NOTCH FILTER CONFIG ---
NOTCH_FREQUENCY = 60            # Frequency to remove (Hz) - typically 50Hz or 60Hz hum
NOTCH_Q = 10                    # Quality factor (higher = narrower notch)

# --- GAIN CONFIG ---
GAIN_DB = 0.0                   # Gain in dB (positive = amplify, negative = reduce)

# --- UI SETTINGS ---
VISUAL_THROTTLE = 0.1  # Update frequency for visual indicators (seconds)

# --- SOCKET CONFIG ---
SOCKET_RECV_BUFFER = 256  # Ultra-minimal buffer to prevent accumulation
SOCKET_SEND_BUFFER = 256  # Ultra-minimal buffer to prevent accumulation
