import os
import sys
import json
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.streaming.streaming_engine import stream_tony_response
from apps.backend.voice.ux_optimizer import GLOBAL_VOICE_UX

def run_verification():
    print("=== TONY PREMIUM VOICE UX AUDIT ===\n")

    # 1. Latency Filler Verification
    print("[TEST 1] Latency Filler Emission")
    filler = GLOBAL_VOICE_UX.get_filler_phrase()
    print(f"  -> Sample Filler: '{filler}'")
    assert any(f in filler for f in ["moment", "think", "second", "check"])
    print("  -> Latency masking fillers verified.")

    # 2. Conversational Contractions Verification
    print("\n[TEST 2] Text-to-Speech Smoothing (Contractions)")
    raw_text = "I am happy because it is working. I do not think there is a problem."
    optimized = GLOBAL_VOICE_UX.optimize_text_for_speech(raw_text)
    print(f"  -> Raw: {raw_text}")
    print(f"  -> Optimized: {optimized}")
    assert "I'm" in optimized
    assert "it's" in optimized
    assert "don't" in optimized
    print("  -> Tone optimization (contractions) verified.")

    # 3. Stream Integration Audit
    print("\n[TEST 3] End-to-End Stream UX Injection")
    with patch("apps.backend.streaming.streaming_engine.run_llm_inference_stream", return_value=[" It is fine."]), \
         patch("apps.backend.cognition.cognitive_controller.CognitiveController.run_cognitive_pipeline", return_value=MagicMock(module_outputs={})):
        
        gen = stream_tony_response("Test", {"interface": "voice"})
        events = list(gen)
        
        # First token should be a filler phrase (sequence_index -1)
        first_token_event = next(e for e in events if e.event_type == "token")
        print(f"  -> First Token Yieled: '{first_token_event.content}'")
        assert any(f in first_token_event.content for f in ["moment", "think", "second"])
        
        # Final tokens should be optimized
        token_events = [e.content for e in events if e.event_type == "token"]
        token_events_lower = [t.lower() for t in token_events]
        print(f"  -> All Tokens (lower): {token_events_lower}")
        # "It is fine" from mock should become "it's fine"
        assert any("it's" in t for t in token_events_lower)
    
    print("  -> Stream UX (Fillers + Smoothing) verified.")

    print("\n=== AUDIT SUCCESSFUL ===")

if __name__ == "__main__":
    run_verification()
