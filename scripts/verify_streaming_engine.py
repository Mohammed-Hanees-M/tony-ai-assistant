import os
import sys
import json
import time
from unittest.mock import patch, MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.streaming.streaming_engine import stream_tony_response, cancel_stream
from apps.backend.schemas.cognition import CognitivePlan, CognitiveStep, CognitiveTrace, CognitiveExchange

def mock_inference_stream(messages, model):
    tokens = ["Hello", " ", "I", " ", "am", " ", "Tony.", " ", "How", " ", "can", " ", "I", " ", "help?"]
    for t in tokens:
        time.sleep(0.1) # Simulate network delay
        yield t

def run_verification():
    print("=== TONY STREAMING ENGINE VERIFICATION (PART 9A) ===\n")
    
    # 1. Success Stream Test
    print("[TEST A, B, F] Incremental Streaming & Sequence Integrity")
    
    with patch("apps.backend.streaming.streaming_engine.run_llm_inference_stream", side_effect=mock_inference_stream), \
         patch("apps.backend.cognition.cognitive_controller.run_llm_inference", return_value=json.dumps({
             "pipeline_mode": "direct",
             "required_modules": ["memory"],
             "execution_order": [{"module_name": "memory", "description": "1", "order_index": 1}]
         })):
        
        events = list(stream_tony_response("Who are you?"))
        
        # Verify event types
        event_types = [e.event_type for e in events]
        assert "meta" in event_types
        assert "token" in event_types
        assert "done" in event_types
        
        # Verify sequence indices
        indices = [e.sequence_index for e in events]
        assert indices == sorted(indices), "Sequence indices are out of order!"
        
        # Verify final content
        done_event = events[-1]
        assert "Tony" in done_event.content["final_result"]
        print("  -> Tokens received incrementally.")
        print("  -> Sequence integrity verified.")
        print("  -> Final 'done' event contains result and trace.\n")

    # 2. Cancellation Test
    print("[TEST D] Stream Cancellation")
    
    with patch("apps.backend.streaming.streaming_engine.run_llm_inference_stream", side_effect=mock_inference_stream):
        stream_gen = stream_tony_response("Cancel me")
        
        captured_events = []
        stream_id = None
        
        for e in stream_gen:
            captured_events.append(e)
            if e.event_type == "meta" and "stream_id" in e.content:
                stream_id = e.content["stream_id"]
            
            # Trigger cancellation after first token
            if e.event_type == "token":
                print(f"  -> Cancelling stream {stream_id}...")
                cancel_stream(stream_id)
        
        event_types = [e.event_type for e in captured_events]
        assert "interrupted" in event_types
        assert "done" not in event_types
        print("Test D Passed: Stream halted and emitted 'interrupted' event.\n")

    # 3. Trace Preservation
    print("[TEST E] Cognitive Trace Preservation")
    last_event = events[-1]
    assert "trace" in last_event.content
    assert "memory" in last_event.content["trace"]["module_outputs"]
    print("Test E Passed: Full cognitive lineage attached to 'done' event.\n")

    print("\n=== EXAMPLE STREAM EVENT DUMP (Meta) ===")
    print(events[0].model_dump_json(indent=2))

    print("\n=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    run_verification()
