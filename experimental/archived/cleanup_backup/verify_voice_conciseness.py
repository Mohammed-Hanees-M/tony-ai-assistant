import os
import sys
import json
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.streaming.streaming_engine import stream_tony_response

def run_verification():
    print("=== TONY VOICE RESPONSE OPTIMIZATION AUDIT ===\n")

    # Mocking inference to track the system prompt and verify limit enforcement
    with patch("apps.backend.streaming.streaming_engine.run_llm_inference_stream") as mock_stream, \
         patch("apps.backend.cognition.cognitive_controller.CognitiveController.run_cognitive_pipeline") as mock_brain:
        
        # 1. Mock a complex response that SHOULD be trimmed by the prompt/engine
        long_text = ["This", " is", " a", " very", " long", " response", " that", " should", " eventually", " be", " cut", " off", " because", " it", " is", " in", " voice", " mode", " and", " we", " want", " to", " be", " concise", " and", " not", " speak", " for", " too", " long", " to", " the", " user", " unless", " they", " specifically", " asked", " for", " it", " which", " they", " did", " not", " here.", " extra", " tokens", " here", " to", " trigger", " the", " break.", " and", " more", " and", " more."]
        mock_stream.return_value = long_text
        mock_brain.return_value = MagicMock(module_outputs={})
        
        print("[TEST 1] Verifying Voice Mode Brevity Enforcement")
        # Interface = voice triggers BREVITY
        gen = stream_tony_response("Tell me a long story", {"interface": "voice"})
        
        tokens = []
        for event in gen:
            if event.event_type == "token":
                tokens.append(event.content)
        
        print(f"  -> Generated {len(tokens)} tokens.")
        # Total tokens yielded should be limited by the logic (seq > 50)
        # Note: sequence starts at 2. So roughly 48 tokens allowed.
        assert len(tokens) <= 50, f"Response too long for voice mode! {len(tokens)} tokens"
        print("  -> Hard token limit verified.")

        # 2. Verify System Prompt Injection
        # Ensure the stream was actually called and capture the arguments
        if mock_stream.called:
            args, kwargs = mock_stream.call_args
            last_messages = args[0]
            sys_prompt = next(m["content"] for m in last_messages if m["role"] == "system")
            
            print("[TEST 2] Verifying System Prompt Specialization")
            assert "VOICE MODE ACTIVE" in sys_prompt
            assert "1-2 short sentences" in sys_prompt
            print("  -> Voice-specific persona guidelines found in prompt.")
        else:
            print("[ERROR] LLM stream was never called!")
            assert False

    print("\n=== AUDIT SUCCESSFUL ===")

if __name__ == "__main__":
    run_verification()
