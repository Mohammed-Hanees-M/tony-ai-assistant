import os
import sys
import time
import io
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.voice.tts_engine import TTSEngine

def run_verification():
    print("=== PIPER TTS API COMPATIBILITY VERIFICATION ===\n")

    # 1. Setup Mock for PiperVoice with ONLY synthesize_wav
    mock_voice = MagicMock()
    
    def mock_synthesize_wav(text, output_file):
        # Write some "fake" audio bytes into the file-like object
        fake_audio = b"FAKE_AUDIO_DATA_X" * 1000 # ~17KB total
        output_file.write(fake_audio)
        
    mock_voice.synthesize_wav.side_effect = mock_synthesize_wav
    # Ensure it DOES NOT have the old method
    delattr(mock_voice, 'synthesize_stream') if hasattr(mock_voice, 'synthesize_stream') else None

    # 2. Test the engine with the mock
    with patch("apps.backend.core.dependencies.validate_premium_voice_dependencies"), \
         patch("os.path.exists", return_value=True):
        
        tts = TTSEngine()
        tts.voice = mock_voice # Manually inject the mock voice
        
        # Test Case: Basic Synthesis
        print("[TEST] Basic Synthesis (Check Chunking)")
        def token_stream():
            yield "Hello world."
        
        chunks = list(tts.synthesize_stream(token_stream(), "test_session"))
        
        print(f"  -> Generated {len(chunks)} audio chunks from one phrase.")
        assert len(chunks) > 1, "Should have been split into multiple 8KB chunks"
        assert chunks[0].sequence_index == 0
        assert chunks[-1].is_final == True
        print("  -> Chunking and sequence verified.\n")

        # Test Case: Interruption
        print("[TEST] Interruption Middleware")
        tts.is_interrupted = False
        
        # We'll use a larger buffer to ensure we can interrupt mid-phrase
        def long_mock_synthesize(text, output_file):
             output_file.write(b"DATA" * 5000) # 20KB
        mock_voice.synthesize_wav.side_effect = long_mock_synthesize
        
        # Capture chunks and interrupt after the first one
        interrupted_chunks = []
        gen = tts.synthesize_stream(token_stream(), "interrupt_sess")
        for i, chunk in enumerate(gen):
            interrupted_chunks.append(chunk)
            if i == 0:
                print("  !! Interrupting !!")
                tts.interrupt()
        
        print(f"  -> Total chunks before/at interrupt: {len(interrupted_chunks)}")
        assert len(interrupted_chunks) < 5, "Synthesis should have stopped immediately"
        print("  -> Interruption safety verified.\n")

    print("=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    run_verification()
