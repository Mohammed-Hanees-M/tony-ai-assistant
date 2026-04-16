import os
import sys
import json
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.reasoning.reasoner import parse_and_validate_trace

def run_verification():
    print("=== TONY NESTED REASONING PARSER AUDIT ===\n")

    # Scenario: LLM returns a dictionary for final_conclusion instead of a string
    nested_output = {
        "steps": [
            {
                "thought": {"raw": "I am thinking"},
                "rationale": "Logical necessity",
                "intermediate_result": "2",
                "order_index": 1
            }
        ],
        "final_conclusion": {"message": "While I cannot hear you physically, I am here and ready to help!"},
        "confidence": 0.99
    }
    
    raw_json = json.dumps(nested_output)
    print(f"[TEST 1] Parsing Nested JSON Output")
    
    trace = parse_and_validate_trace(raw_json, "Can you hear me?")
    
    print(f"  -> Extracted Conclusion: '{trace.final_conclusion}'")
    assert trace.final_conclusion == "While I cannot hear you physically, I am here and ready to help!"
    
    print(f"  -> Extracted Thought: '{trace.steps[0].thought}'")
    assert trace.steps[0].thought == "I am thinking"
    
    print("  -> Nested value extraction verified.")

    # Scenario: LLM returns an array of tokens instead of a string (rare but possible)
    array_output = {
        "final_conclusion": ["The", " answer", " is", " yes."],
        "confidence": 0.5
    }
    print(f"\n[TEST 2] Parsing Array-based Output")
    trace = parse_and_validate_trace(json.dumps(array_output), "Test?")
    print(f"  -> Extracted Conclusion: '{trace.final_conclusion}'")
    assert trace.final_conclusion == "The  answer  is  yes."
    print("  -> Array serialization verified.")

    print("\n=== AUDIT SUCCESSFUL ===")

if __name__ == "__main__":
    run_verification()
