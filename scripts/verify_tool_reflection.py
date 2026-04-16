import os
import sys
import json
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.schemas.tool import ToolRoutingDecision, ToolExecutionTrace, ToolExecutionResult, ToolSelection
from apps.backend.tools.tool_reflector import reflect_on_execution, get_persisted_reflections

def mock_inference(messages, model):
    content = messages[-1]["content"]
    
    if "Success Test" in content:
        # A. Useful lesson generated
        return json.dumps({
            "lesson": "Document reading followed by python execution works well.",
            "context_pattern": "Data analysis",
            "tool_pattern": "document_reader -> python_interpreter",
            "success_case": True,
            "confidence": 0.8
        })
    elif "Failure Repeat" in content:
        # B & D. Repeated failure generates and merges
        return json.dumps({
            "lesson": "Python parser fails on malformed CSV strings.",
            "context_pattern": "Broken CSV data",
            "tool_pattern": "python_interpreter_malformed",
            "success_case": False,
            "confidence": 0.95
        })
    elif "One-Off Noise" in content:
        # C. One-off noise (low confidence failure = noise filter catch)
        return json.dumps({
            "lesson": "Maybe the network dropped?",
            "context_pattern": "Network timeouts",
            "tool_pattern": "web_search_timeout",
            "success_case": False,
            "confidence": 0.3
        })
    elif "Filter Pattern" in content:
        # C. Explicit NO_LESSON string
        return "NO_LESSON"

    return "NO_LESSON"


def run_verification():
    print("=== TONY TOOL REFLECTION VERIFICATION (PART 8F) ===\n")
    
    with patch("apps.backend.tools.tool_reflector.run_llm_inference", side_effect=mock_inference):
        
        d_dummy = ToolRoutingDecision(requires_tools=True)
        t_dummy = ToolExecutionTrace(results=[ToolExecutionResult(tool_name="dummy", success=True)])
        
        # A. Successful multi-tool pipeline generates useful lesson
        print("[TEST A] Successful Execution Generation")
        ref_a = reflect_on_execution("Success Test Pipeline", d_dummy, t_dummy)
        assert ref_a.success_case is True
        print("Test A Passed")
        
        # B. Repeated tool failure generates cautionary lesson
        print("\n[TEST B] Cautionary Lesson Generation")
        ref_b = reflect_on_execution("Failure Repeat 1", d_dummy, t_dummy)
        assert ref_b.success_case is False
        assert ref_b.confidence == 0.95
        print("Test B Passed")
        
        # D. Duplicate lessons merge/reinforce
        print("\n[TEST D] Duplicate Lesson Merging")
        ref_d = reflect_on_execution("Failure Repeat 2", d_dummy, t_dummy)
        assert "Reinforced" in ref_d.lesson
        assert ref_d.confidence > 0.95 # Confidence bumped
        assert len(ref_d.supporting_examples) == 2
        print("Test D Passed")
        
        # C-1. Noise Filtering (Low Confidence Failure)
        print("\n[TEST C.1] Noise Filtering (Low Conf)")
        ref_c1 = reflect_on_execution("One-Off Noise event", d_dummy, t_dummy)
        assert ref_c1 is None
        print("Test C.1 Passed")
        
        # C-2. Noise Filtering (Explicit NO_LESSON)
        print("\n[TEST C.2] Noise Filtering (NO_LESSON)")
        ref_c2 = reflect_on_execution("Filter Pattern standard issue", d_dummy, t_dummy)
        assert ref_c2 is None
        print("Test C.2 Passed")
        
        # E. Structured reflection saved correctly & F. Persistence Retrieval ready
        print("\n[TEST E & F] Memory Retrieval")
        saved = get_persisted_reflections()
        assert len(saved) == 2 # Success Test and Failure Repeat (merged)
        print("Test E & F Passed")
        
        print("\n=== RAW REFLECTION DB DUMP ===")
        for r in saved:
            print(r.model_dump_json(indent=2))

    print("\n=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    run_verification()
