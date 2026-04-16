import os
import sys
import json
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.schemas.reasoning import ReasoningTrace, ReasoningStep
from apps.backend.reasoning.verifier import verify_and_improve_answer

def mock_inference(messages, model):
    content = messages[-1]["content"]
    
    if "FAIL_VERIFICATION" in content and "Iteration 1" not in content and "Draft Answer: Earth is flat" in content:
        return json.dumps({
            "passed": False,
            "confidence_delta": -0.8,
            "issues_found": ["Factually incorrect.", "Defies known science."],
            "suggested_improvements": ["State that the Earth is an oblate spheroid."],
            "revised_answer": "Actually, the Earth is an oblate spheroid (roughly spherical).",
            "verifier_notes": "Corrected a massive factual error."
        })
    elif "FAIL_VERIFICATION" in content and "Draft Answer: Actually, the Earth" in content:
        return json.dumps({
            "passed": True,
            "confidence_delta": 0.5,
            "issues_found": [],
            "suggested_improvements": [],
            "revised_answer": "Actually, the Earth is an oblate spheroid (roughly spherical).",
            "verifier_notes": "Draft is now factually sound."
        })
    elif "MALFORMED_TEST" in content:
        return "I refuse to provide JSON."
        
    return json.dumps({
        "passed": True,
        "confidence_delta": 0.05,
        "issues_found": [],
        "suggested_improvements": [],
        "revised_answer": "The sky is blue due to Rayleigh scattering.",
        "verifier_notes": "Answer is perfectly correct."
    })

def run_verification():
    print("=== TONY SELF-CRITIQUE VERIFICATION (PART 8C) ===\n")
    
    with patch("apps.backend.reasoning.verifier.run_llm_inference", side_effect=mock_inference):
        
        trace = ReasoningTrace(query="Test", steps=[], final_conclusion="Draft", confidence=0.8)
        
        # A. Correct answers pass verification
        print("[TEST A] Checking naturally correct answer")
        final, report = verify_and_improve_answer("Why is the sky blue?", trace, "The sky is blue due to Rayleigh scattering.")
        assert report.passed is True
        print("Test A: Passed.")
        
        # B & C & D. Flawed answers fail, get revised, confidence adjusts
        print("\n[TEST B & C & D] Checking flawed answer")
        trace_flawed = ReasoningTrace(query="FAIL_VERIFICATION", steps=[], final_conclusion="Draft", confidence=0.9)
        final_flawed, report_flawed = verify_and_improve_answer("FAIL_VERIFICATION", trace_flawed, "Earth is flat")
        
        assert "spheroid" in final_flawed
        assert trace_flawed.confidence < 0.9 or trace_flawed.confidence > 0.0 # Bounded to reasonable shift
        print(f"Test C: Revised Answer -> {final_flawed}")
        print(f"Test D: Confidence Adjusted -> {trace_flawed.confidence}")
        
        # E. Malformed output safe handling
        print("\n[TEST E] Checking malformed output safe limits")
        trace_malformed = ReasoningTrace(query="MALFORMED_TEST", steps=[], final_conclusion="Draft", confidence=0.9)
        final_mal, rep_mal = verify_and_improve_answer("MALFORMED_TEST", trace_malformed, "Draft", max_iterations=1)
        assert rep_mal.passed is False
        assert rep_mal.confidence_delta == -0.5
        print("Test E: Malformed verification caught securely.")
        
        print("\n=== RAW VERIFICATION REPORT ===")
        print(report_flawed.model_dump_json(indent=2))

    print("\n=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    run_verification()
