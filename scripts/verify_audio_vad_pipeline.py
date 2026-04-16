import os
import sys
import numpy as np
import time
from typing import List

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from apps.backend.voice.audio_capture import AudioCapture
    from apps.backend.voice.vad_engine import VADEngine
except ImportError as e:
    print(f"[FATAL] Import error: {e}")
    sys.exit(1)

def generate_synthetic_speech(duration_s: float, sample_rate: int = 16000) -> np.ndarray:
    """Generates a noisy signal to simulate 'speech'."""
    t = np.linspace(0, duration_s, int(sample_rate * duration_s))
    # Mix of frequencies + noise
    speech = 0.5 * np.sin(2 * np.pi * 440 * t) + 0.2 * np.random.normal(0, 0.1, len(t))
    return speech.astype(np.float32)

def generate_silence(duration_s: float, sample_rate: int = 16000) -> np.ndarray:
    return np.zeros(int(sample_rate * duration_s), dtype=np.float32)

def run_verification():
    print("=== TONY AUDIO & VAD PIPELINE VERIFICATION (PART 1) ===\n")
    
    vad = VADEngine(threshold=0.3, use_model=False)
    chunk_size = 512
    sample_rate = 16000

    # 1. Create a synthetic stream: 1s Silence -> 1.5s Speech -> 1.5s Silence
    print("[STEP 1] Generating synthetic audio signal...")
    signal = np.concatenate([
        generate_silence(1.0, sample_rate),
        generate_synthetic_speech(1.5, sample_rate),
        generate_silence(1.5, sample_rate)
    ])
    
    # 2. Process chunks
    utterances_found = 0
    start_found = False
    
    print("[STEP 2] Processing audio chunks through VAD...")
    for i in range(0, len(signal), chunk_size):
        chunk = signal[i:i+chunk_size]
        if len(chunk) < chunk_size: break
        
        # Reshape to (512, 1) to match sounddevice indata format
        result = vad.process_chunk(chunk.reshape(-1, 1))
        
        if vad.is_triggered() and not start_found:
            print(f"  -> Speech detection started at {i/sample_rate:.2f}s")
            start_found = True
            
        if result is not None:
            utterances_found += 1
            print(f"  -> Utterance finalized! Size: {len(result)} samples ({len(result)/sample_rate:.2f}s)")
            assert len(result) > sample_rate, "Utterance too short!"

    print("\n[STEP 3] Validations")
    assert utterances_found == 1, f"Expected 1 utterance, found {utterances_found}"
    print("  -> VAD Speech/Silence segmentation verified.")
    print("  -> Buffer concatenation verified.")

    print("\n=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    run_verification()
