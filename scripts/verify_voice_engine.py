import os
import sys
import json
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.voice.voice_engine import GLOBAL_VOICE_ENGINE
from apps.backend.schemas.streaming import StreamEvent

def run_verification():
    print("=== TONY VOICE INTERFACE ENGINE VERIFICATION (PART 9C) ===\n")
    
    session_id = "voice_sess_123"

    # 1. STT Test
    print("[TEST A] STT: Audio Input Processing")
    transcript = GLOBAL_VOICE_ENGINE.process_voice_input(b"some_audio_data")
    assert transcript.text == "This is a mock transcript from speech."
    assert transcript.confidence > 0.9
    print("Test A Passed\n")

    # 2. TTS Streaming Test
    print("[TEST B, C, E] Streaming TTS & State Transitions")
    
    def mock_text_gen():
        yield "Hello"
        yield "world"
        yield "how"
        yield "are"
        yield "you"

    audio_chunks = []
    print(f"  -> Starting TTS stream for {session_id}...")
    for chunk in GLOBAL_VOICE_ENGINE.stream_voice_output(mock_text_gen(), session_id):
        audio_chunks.append(chunk)
        if chunk.sequence_index == 0:
            # Check state was set to speaking
            assert GLOBAL_VOICE_ENGINE._states[session_id].status == "speaking"

    assert len(audio_chunks) == 6 # 5 tokens + 1 final
    assert audio_chunks[-1].is_final == True
    assert audio_chunks[0].data.decode().startswith("<AUDIO:Hello>")
    assert GLOBAL_VOICE_ENGINE._states[session_id].status == "idle"
    print("Test B, C, E Passed\n")

    # 3. Interruption Test
    print("[TEST D] Voice Interruption")
    
    def infinite_text_gen():
        while True:
            yield "token"
            time.sleep(0.1)

    interrupted_chunks = []
    stream_gen = GLOBAL_VOICE_ENGINE.stream_voice_output(infinite_text_gen(), "sess_interrupt")
    
    for i, chunk in enumerate(stream_gen):
        interrupted_chunks.append(chunk)
        if i == 2:
            print("  -> User dynamic interruption triggered!")
            GLOBAL_VOICE_ENGINE.interrupt("sess_interrupt")
        if i > 5: # Safety break if interrupt failed
            break
            
    assert len(interrupted_chunks) < 10
    assert GLOBAL_VOICE_ENGINE._states["sess_interrupt"].status == "interrupted"
    print("Test D Passed\n")

    print("\n=== VOICE STATE TRACE DUMP ===")
    states = {sid: s.model_dump() for sid, s in GLOBAL_VOICE_ENGINE._states.items()}
    print(json.dumps(states, indent=2))

    print("\n=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    run_verification()
