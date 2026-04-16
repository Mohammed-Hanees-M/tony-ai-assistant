import os
import sys
import numpy as np
import time
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.voice.tts_engine import TTSEngine

def run_verification():
    print("=== TONY AUDIO OUTPUT AUDIT (PART 9D.7) ===\n")

    # 1. Pipeline components
    # Patch dependencies to allow instantiation in limited environments
    with patch("apps.backend.core.dependencies.validate_premium_voice_dependencies"), \
         patch("os.path.exists", return_value=True):
        tts = TTSEngine()

    # 2. Simulate Piper returning valid WAV
    print("[STEP 1] Generating Synthetic PCM from Engine...")
    mock_voice = MagicMock()
    def mock_synthesize(text, wav_file):
        # Generate 1s of 440Hz sine wave int16 PCM
        sr = 22050
        t = np.linspace(0, 1.0, sr)
        audio = (np.sin(2 * np.pi * 440 * t) * 10000).astype(np.int16)
        
        import wave
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sr)
        wav_file.writeframes(audio.tobytes())
        
    mock_voice.synthesize_wav.side_effect = mock_synthesize
    tts.voice = mock_voice

    phrase_gen = (p for p in ["Audio output test."])
    chunks = list(tts.synthesize_stream(phrase_gen, "test_audio_out"))
    
    # 3. Validation Logic
    print("[STEP 2] Auditing Chunk Formats...")
    for i, chunk in enumerate(chunks):
        # A. Verify it's RAW PCM not WAV header
        # PCM should NOT start with RIFF if properly extracted
        assert not chunk.data.startswith(b"RIFF"), f"Chunk {i} still contains WAV header!"
        
        # B. Verify Dtype matches int16 (even byte count)
        assert len(chunk.data) % 2 == 0, f"Chunk {i} has odd byte count (corrupt PCM)!"
        
        # C. Verify Volume (non-silent)
        audio_np = np.frombuffer(chunk.data, dtype=np.int16)
        rms = np.sqrt(np.mean(audio_np.astype(np.float32)**2))
        print(f"  -> Chunk {i}: RMS={rms:.2f}, Samples={len(audio_np)}")
        assert rms > 100.0, f"Chunk {i} is unnaturally silent!"

    # 4. Simulated Playback check
    print("\n[STEP 3] Verifying Playback conversion...")
    # This simulates the logic in live_voice_test.py
    audio_f32 = audio_np.astype(np.float32) / 32768.0
    print(f"  -> Conversion to Float32: Min={np.min(audio_f32):.4f}, Max={np.max(audio_f32):.4f}")
    assert np.max(np.abs(audio_f32)) <= 1.0, "Audio clipping during FLOAT32 conversion!"
    assert np.max(np.abs(audio_f32)) > 0.0, "Audio silence after FLOAT32 conversion!"

    print("\n=== AUDIO OUTPUT AUDIT SUCCESSFUL ===")

if __name__ == "__main__":
    run_verification()
