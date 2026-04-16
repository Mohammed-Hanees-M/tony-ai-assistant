import os
import sys
import time
import io
import wave
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.voice.tts_engine import TTSEngine

def run_verification():
    print("=== PIPER WAVE WRAPPER COMPATIBILITY VERIFICATION ===\n")

    # 1. Setup Mock for PiperVoice
    mock_voice = MagicMock()
    
    def mock_synthesize_wav(text, wav_file):
        # SIMULATE PIPER BEHAVIOR: 
        # It calls wave methods on the passed object
        print("  [MOCK] Piper calling wav_file.setframerate(22050)...")
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(22050)
        wav_file.writeframes(b"FAKE_PCM_DATA" * 500) # ~6.5KB
        
    mock_voice.synthesize_wav.side_effect = mock_synthesize_wav

    # 2. Test the engine
    with patch("apps.backend.core.dependencies.validate_premium_voice_dependencies"), \
         patch("os.path.exists", return_value=True):
        
        tts = TTSEngine()
        tts.voice = mock_voice
        
        print("[TEST] Synthesis with Wave Wrapper")
        def token_stream():
             yield "Testing wave wrapper."
             
        chunks = list(tts.synthesize_stream(token_stream(), "test_session"))
        
        print(f"  -> Generated {len(chunks)} audio chunks.")
        assert len(chunks) >= 1
        # Check that data contains the wav header if it was written via wave.open
        # Usually wave.open with BytesIO results in a header at the start
        assert b"RIFF" in chunks[0].data
        print("  -> Wave header and data integrity verified.\n")

    print("=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    run_verification()
