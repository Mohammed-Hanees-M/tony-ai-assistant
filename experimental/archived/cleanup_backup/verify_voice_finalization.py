import os
import sys
import time
import uuid
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.voice.tts_engine import TTSEngine
from apps.backend.streaming.streaming_engine import stream_tony_response
from apps.backend.schemas.cognition import CognitivePlan, CognitiveStep

def run_verification():
    print("=== TONY VOICE ORCHESTRATION FINALIZATION VERIFICATION ===\n")

    # 1. Single Brain Planning Verification
    print("[TEST 1] Single Brain Planning Guarantee")
    
    # We'll use a real stream call and watch the planning logs
    # We patch the planner print to count occurrences
    with patch("apps.backend.cognition.cognitive_controller.run_llm_inference", return_value='{"pipeline_mode": "direct"}'):
        # We need a dummy generator for run_llm_inference_stream too
        with patch("apps.backend.streaming.streaming_engine.run_llm_inference_stream", return_value=[" Hello"]):
            # Count calls to CognitiveController._generate_plan
            # We return a real instance of CognitivePlan
            mock_plan_obj = CognitivePlan(
                pipeline_mode="direct",
                required_modules=["reasoning"],
                execution_order=[CognitiveStep(module_name="reasoning", order_index=1, description="Test")]
            )
            with patch("apps.backend.cognition.cognitive_controller.CognitiveController._generate_plan", 
                       return_value=mock_plan_obj) as mock_plan:
                
                # Consume the stream
                list(stream_tony_response("Hi Tony", {}))
                
                print(f"  -> _generate_plan called {mock_plan.call_count} time(s).")
                assert mock_plan.call_count == 1, "Brain planning called more than once!"
    print("  -> Single planning check passed.")

    # 2. Globally Monotonic Sequencing (Gapless)
    print("\n[TEST 2] Global Monotonic Sequence Indexing (Gapless)")
    tts = TTSEngine()
    
    mock_voice = MagicMock()
    def mock_synthesize(text, wav_file):
        # 20KB = ~3 chunks (8KB each)
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(22050)
        wav_file.writeframes(b"DATA" * 5000)
    mock_voice.synthesize_wav.side_effect = mock_synthesize
    tts.voice = mock_voice
    
    def phrase_stream():
        yield "This is phrase one."
        yield "And this is phrase two."
        
    chunks = list(tts.synthesize_stream(phrase_stream(), "final_verify"))
    
    indices = [c.sequence_index for c in chunks]
    print(f"  -> Sequence Indices: {indices}")
    
    # Must be 0, 1, 2, 3...
    assert indices == list(range(len(indices))), f"Sequence is not continuous! Found: {indices}"
    print("  -> Gapless monotonic sequencing verified.")

    # 3. Interruption Integrity
    print("\n[TEST 3] Interruption Handling")
    tts.is_interrupted = False
    interrupted_chunks = []
    
    # Simulate a stream that we stop halfway
    gen = tts.synthesize_stream(phrase_stream(), "interrupt_sess")
    for i, chunk in enumerate(gen):
        interrupted_chunks.append(chunk)
        if i == 1:
            tts.interrupt()
            
    print(f"  -> Chunks delivered before/at halt: {len(interrupted_chunks)}")
    assert len(interrupted_chunks) < 6, "Failed to halt delivery immediately"
    print("  -> Interruption integrity verified.")

    print("\n=== FINALIZATION SUCCESSFUL ===")

if __name__ == "__main__":
    run_verification()
