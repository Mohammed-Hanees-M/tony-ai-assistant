import os
import sys
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.reasoning.reasoner import generate_reasoned_response

VALID_JSON_RESPONSE = """
{
  "steps": [
    {
      "order_index": 1,
      "thought": "I need to determine the capital of France.",
      "rationale": "The user is asking a direct geographical question.",
      "intermediate_result": "The country is France. I must find its capital."
    },
    {
      "order_index": 2,
      "thought": "Recall geographical facts about France.",
      "rationale": "Memory retrieval shows Paris is the capital.",
      "intermediate_result": "Paris"
    }
  ],
  "final_conclusion": "The capital of France is Paris.",
  "confidence": 0.99
}
"""

INVALID_JSON_RESPONSE = "This is just plain text. I refuse to output JSON."

def mock_inference(messages, model):
    content = messages[-1]["content"]
    if "FAIL_TEST" in content:
        return INVALID_JSON_RESPONSE
    return VALID_JSON_RESPONSE

def run_verification():
    print("=== TONY MULTI-STEP REASONING VERIFICATION (PART 8B) ===\n")
    
    with patch("apps.backend.reasoning.reasoner.run_llm_inference", side_effect=mock_inference):
        query = "What is the capital of France?"
        context = {"history": []}
        
        # Test valid parsing
        final_answer, trace = generate_reasoned_response(query, context)
        
        # A. Complex question generates multiple reasoning steps
        print(f"Test A: Trace generated with {len(trace.steps)} reasoning steps.")
        assert len(trace.steps) == 2, "Failed to generate multiple steps"
        
        # B. Steps logically ordered
        print("Test B: Steps logically ordered.")
        assert trace.steps[0].order_index == 1
        assert trace.steps[1].order_index == 2
        
        # C. Intermediate results populated
        print(f"Test C: Intermediate result populated: '{trace.steps[1].intermediate_result}'")
        assert trace.steps[0].intermediate_result == "The country is France. I must find its capital."
        assert trace.steps[1].intermediate_result == "Paris"
        
        # D. Final conclusion derived from trace
        print(f"Test D: Final conclusion matched. -> '{final_answer}'")
        assert final_answer == "The capital of France is Paris."
        
        # F. Hidden trace works (return only answer)
        print("Test F: Internal hidden trace separation works natively.")
        assert isinstance(final_answer, str)
        assert hasattr(trace, 'steps')
        
        # E. Malformed output handled safely
        print("\n[Simulating Invalid Output]")
        safe_answer, safe_trace = generate_reasoned_response("FAIL_TEST", context)
        print(f"Test E: Invalid output safe fallback: '{safe_answer}' (conf: {safe_trace.confidence})")
        assert safe_trace.confidence == 0.1
        assert safe_answer == "This is just plain text. I refuse to output JSON."
        assert len(safe_trace.steps) == 1
        
        print("\n=== RAW REASONING TRACE DUMP ===")
        print(trace.model_dump_json(indent=2))

    print("\n=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    run_verification()
