import os
import sys
import time
import uuid
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.voice.tts_engine import TTSEngine
from apps.backend.voice.voice_engine import GLOBAL_VOICE_ENGINE
from apps.backend.schemas.voice import AudioChunk

def run_verification():
    print("=== TONY AUDIO CHUNK INTEGRITY AUDIT ===\n")

    # 1. Thread-Safe Lock Verification
    print("[TEST 1] Thread-Safe Pipeline Lock")
    session_id = "test_lock_session"
    GLOBAL_VOICE_ENGINE.release_pipeline_lock(session_id)
    
    # We simulate simultaneous calls to acquire_pipeline_lock
    import threading
    results = []
    def try_acquire():
        results.append(GLOBAL_VOICE_ENGINE.acquire_pipeline_lock(session_id))
    
    threads = [threading.Thread(target=try_acquire) for _ in range(10)]
    for t in threads: t.start()
    for t in threads: t.join()
    
    # Exactly one should be True
    success_count = sum(1 for r in results if r is True)
    print(f"  -> Acquisition attempts successful: {success_count}/10")
    assert success_count == 1, "Pipeline lock is not thread-safe!"
    print("  -> Thread-safety verified.")

    # 2. Monotonic Sequence Indexing
    print("\n[TEST 2] Monotonic Sequence Indexing across Phrases")
    tts = TTSEngine()
    
    # Mock PiperVoice to generate some chunks
    mock_voice = MagicMock()
    def mock_synthesize(text, wav_file):
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(22050)
        wav_file.writeframes(b"DATA" * 5000) # Enough for 3 chunks (8KB each)
    mock_voice.synthesize_wav.side_effect = mock_synthesize
    tts.voice = mock_voice
    
    def phrase_gen():
        yield "First phrase."
        yield "Second phrase."
        
    chunks = list(tts.synthesize_stream(phrase_gen(), "test_seq"))
    
    indices = [c.sequence_index for c in chunks]
    print(f"  -> Generated Chunk Indices: {indices}")
    
    # Indices should be unique and strictly increasing
    assert len(indices) == len(set(indices)), "Duplicate sequence indexes detected!"
    # They don't have to be consecutive (since we use phrase_offset + chunk_offset) 
    # but they must be strictly increasing.
    assert all(indices[i] < indices[i+1] for i in range(len(indices)-1)), "Indices are not strictly increasing!"
    print("  -> Monotonic globally unique indexing verified.")

    # 3. Data Integrity (No Payload Re-use)
    print("\n[TEST 3] Payload Uniqueness")
    # Verify metadata differentiates chunks
    phrase_indices = [c.metadata["phrase_index"] for c in chunks]
    chunk_indices = [c.metadata["chunk_in_phrase"] for c in chunks]
    
    print(f"  -> Phrase IDs: {phrase_indices}")
    print(f"  -> Chunk IDs: {chunk_indices}")
    
    assert 0 in phrase_indices and 1 in phrase_indices
    assert any(ci > 0 for ci in chunk_indices)
    print("  -> Payload/Metadata differentiation verified.")

    print("\n=== AUDIT SUCCESSFUL ===")

if __name__ == "__main__":
    run_verification()
