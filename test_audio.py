import socket
import threading
import pyaudio
import audioop  # Used to calculate volume level
import time
import select
import struct
import numpy as np

# --- CONFIGURATION FOR LOW LATENCY (NO BUFFER BUILDUP) ---
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

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# Ultra-minimal buffers to prevent accumulation
sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 256)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 256)
# NON-BLOCKING mode: recv returns immediately if no data (prevents blocking on full buffer)
sock.setblocking(False)
sock.bind(('0.0.0.0', PORT))

_LAST_VISUAL = 0.0
VISUAL_THROTTLE = 0.1
_RECV_QUEUE_DEPTH = 0  # Monitor incoming packet backlog
_SEND_QUEUE_DEPTH = 0

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
    except Exception as e:
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
    except Exception as e:
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

def pick_microphone(p):
    """ Lists all microphones and asks user to select one """
    print("\n--- Available Microphones ---")
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    input_devices = []

    for i in range(0, numdevices):
        if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            name = p.get_device_info_by_host_api_device_index(0, i).get('name')
            input_devices.append(i)
            print(f"ID {i}: {name}")

    if not input_devices:
        print("❌ No microphone found!")
        exit()
        
    device_id = int(input("\nEnter the ID of the microphone you want to use: "))
    return device_id

def receive_audio(output_stream):
    """Receive and play latest packet only; discard old ones if backlog exists."""
    global _RECV_QUEUE_DEPTH
    
    while True:
        try:
            # Use select() to check if data is ready
            ready = select.select([sock], [], [], 0.01)
            if not ready[0]:
                # No data available
                time.sleep(0.001)
                continue
            
            # Receive the first packet
            data, _ = sock.recvfrom(CHUNK * 4)
            
            # Drain ONLY older packets in buffer; keep the latest one
            drained = 0
            latest_data = data
            while drained < 5:
                try:
                    ready = select.select([sock], [], [], 0)
                    if not ready[0]:
                        break
                    latest_data, _ = sock.recvfrom(CHUNK * 4)
                    drained += 1
                except BlockingIOError:
                    break
            
            _RECV_QUEUE_DEPTH = drained
            
            # Play ONLY the latest packet (discard old ones)
            try:
                output_stream.write(latest_data)
            except Exception:
                # Overflow; skip this frame only
                pass
                
        except BlockingIOError:
            time.sleep(0.001)
        except Exception as e:
            if "Errno 10054" not in str(e):
                break

def send_audio(input_stream, output_stream, target_ip):
    """Read mic and send immediately for smooth, natural audio."""
    print(f"\n🎤 sending audio to {target_ip}...")
    print(f"(Clean, unprocessed audio for smooth quality)")
    
    global _LAST_VISUAL, _SEND_QUEUE_DEPTH
    while True:
        try:
            # Read one frame from mic
            data = input_stream.read(CHUNK, exception_on_overflow=False)
            
            # Apply noise cancellation (disabled by default for smooth audio)
            data = apply_noise_cancellation(data)
            
            # Send immediately
            try:
                sock.sendto(data, (target_ip, PORT))
                _SEND_QUEUE_DEPTH = 0
            except BlockingIOError:
                _SEND_QUEUE_DEPTH = 1
            
            # Throttled visual update
            now = time.time()
            if now - _LAST_VISUAL >= VISUAL_THROTTLE:
                _LAST_VISUAL = now
                try:
                    rms = audioop.rms(data, 2)  
                    bars = "█" * int((rms / 300))
                    status = f"Vol: {bars[:50].ljust(50)} [Rx:{_RECV_QUEUE_DEPTH}]"
                    print(f"\r{status[:75]}", end="", flush=False)
                except Exception:
                    pass
        except Exception:
            break

def start_voice_chat():
    p = pyaudio.PyAudio()

    # 1. Select Microphone
    input_device_index = pick_microphone(p)

    # CRITICAL: Separate input and output streams to avoid internal buffering delay
    input_stream = p.open(format=FORMAT,
                          channels=CHANNELS,
                          rate=RATE,
                          input=True,
                          input_device_index=input_device_index,
                          frames_per_buffer=CHUNK)

    output_stream = p.open(format=FORMAT,
                           channels=CHANNELS,
                           rate=RATE,
                           output=True,
                           frames_per_buffer=CHUNK)

    target_ip = input("\nEnter the IP address of the OTHER person: ")

    # Start receiver thread  
    listener = threading.Thread(target=receive_audio, args=(output_stream,), daemon=True)
    listener.start()

    # Send on main thread (higher priority, no context switching)
    send_audio(input_stream, output_stream, target_ip)

if __name__ == "__main__":
    start_voice_chat()