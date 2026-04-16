import os
import sys
import time
import json
from unittest.mock import MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.voice.tts_engine import TTSEngine

def run_verification():
    print("=== TONY TTS ENGINE VERIFICATION (PART 3) ===\n")
    
    tts = TTSEngine()

    # 1. Phrase Chunking Test
    print("[TEST B, C, E] Streaming Phrase-based Synthesis")
    def mock_token_stream():
        tokens = ["Hello", " ", "world.", " ", "This", " ", "is", " ", "Tony!"]
        for t in tokens:
            yield t

    chunks = list(tts.synthesize_stream(mock_token_stream(), "test_session"))
    
    print(f"  -> Generated {len(chunks)} audio chunks.")
    assert len(chunks) == 2, f"Expected 2 phrases (Hello world. & This is Tony!), got {len(chunks)}"
    assert chunks[0].metadata["text"] == "Hello world."
    assert chunks[1].metadata["text"] == "This is Tony!"
    print("  -> Phrase chunking and sequencing verified.\n")

    # 2. Interruption Test
    print("[TEST D] Real-time Interruption")
    def slow_token_stream():
        yield "Start."
        time.sleep(1) # Gap for interruption
        yield "Middle."
        yield "End."

    interrupted_chunks = []
    
    # Run in a separate way or manually trigger
    gen = tts.synthesize_stream(slow_token_stream(), "interrupt_sess")
    
    for i, chunk in enumerate(gen):
        interrupted_chunks.append(chunk)
        print(f"  -> Synthesized: {chunk.metadata['text']}")
        if i == 0:
            print("  !! Interruption triggered !!")
            tts.interrupt()
            
    assert len(interrupted_chunks) == 1, f"Expected 1 chunk before interruption, got {len(interrupted_chunks)}"
    print("  -> Interruption halted synthesis successfully.\n")

    print("\n=== AUDIO CHUNK DUMP ===")
    print(chunks[1].model_dump_json(indent=2))

    print("\n=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    run_verification()
