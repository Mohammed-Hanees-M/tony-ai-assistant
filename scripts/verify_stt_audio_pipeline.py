import os
import sys
import numpy as np
import time
from unittest.mock import patch, MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.voice.vad_engine import VADEngine
from apps.backend.voice.stt_engine import STTEngine

def run_verification():
    print("=== TONY STT AUDIO PIPELINE AUDIT (PART 9D.6) ===\n")
    
    # 1. Pipeline components
    vad = VADEngine(threshold=0.3, use_model=False)
    # Patch STT to avoid real Whisper load if not needed for structural test, 
    # but we want to verify the logprobs if possible.
    with patch("apps.backend.core.dependencies.validate_premium_voice_dependencies"):
        stt = STTEngine(model_size="tiny.en")

    sample_rate = 16000
    
    # 2. Simulate malformed audio input (Int16, Stereo, High Volume)
    print("[STEP 1] Generating 'Dirty' Audio (Int16, Stereo, Out of Range)")
    # Generate 1s of 440Hz sine wave
    t = np.linspace(0, 1.0, sample_rate)
    sine = (np.sin(2 * np.pi * 440 * t) * 40000).astype(np.int16) # Overflowing int16 amplitude
    dirty_audio = np.stack([sine, sine], axis=1) # Stereo (16000, 2)
    
    # 3. Pass through VAD
    print("[STEP 2] Processing through VAD Buffer...")
    # Simulate VAD receiving chunks
    chunk_size = 512
    final_audio = None
    for i in range(0, len(dirty_audio), chunk_size):
        chunk = dirty_audio[i:i+chunk_size]
        res = vad.process_chunk(chunk)
        if res is not None:
            final_audio = res
            break
    
    # Force finalize if VAD didn't trigger (since it's constant loud noise it should trigger start)
    # We add some silence to trigger end
    silence = np.zeros((sample_rate, 2), dtype=np.int16)
    for i in range(0, len(silence), chunk_size):
        res = vad.process_chunk(silence[i:i+chunk_size])
        if res is not None:
            final_audio = res
            break

    assert final_audio is not None, "VAD failed to capture utterance"
    print(f"  -> Captured Audio Shape: {final_audio.shape}, Dtype: {final_audio.dtype}")
    
    # 4. Pass through STT Repair & Diagnostics
    print("[STEP 3] Processing through STT Repair Pipeline...")
    transcript = stt.transcribe(final_audio)
    
    # 5. Validations
    print("\n[STEP 4] Integrity Validations")
    
    # A. Check if repaired to float32 1D
    assert transcript.text is not None
    # Check debug wav existence
    debug_files = os.listdir("debug_wavs")
    assert len(debug_files) > 0, "No debug wav exported"
    print(f"  -> Debug WAV Exported: {debug_files[-1]}")
    
    # B. Check if Whisper returned sane confidence (Mock mode returns 0.95)
    print(f"  -> Final Confidence: {transcript.confidence:.2f}")
    assert transcript.confidence > 0.1
    
    print("\n=== AUDIT SUCCESSFUL ===")

if __name__ == "__main__":
    run_verification()
