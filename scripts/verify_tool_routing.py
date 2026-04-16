import os
import sys
import json
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.tools.tool_router import route_tools_for_task

def mock_inference(messages, model):
    content = messages[-1]["content"]
    
    if "latest news" in content.lower():
        # A. Search Query
        return json.dumps({
            "requires_tools": True,
            "selections": [
                {
                    "tool_name": "web_search",
                    "confidence": 0.99,
                    "reason": "Search recent events.",
                    "required_inputs": {"query": "latest news"}
                }
            ],
            "fallback_strategy": "Say I don't know.",
            "reasoning_summary": "Need current data."
        })
    elif "read summary.pdf" in content.lower():
        # B. Document Query
        return json.dumps({
            "requires_tools": True,
            "selections": [
                {
                    "tool_name": "document_reader",
                    "confidence": 0.95,
                    "reason": "Read the file.",
                    "required_inputs": {"file_path": "summary.pdf"}
                }
            ],
            "fallback_strategy": "Ask for copy paste.",
            "reasoning_summary": "User wants document context."
        })
    elif "who are you" in content.lower():
        # C. Coding / direct query
        return json.dumps({
            "requires_tools": False,
            "selections": [],
            "fallback_strategy": "Direct answer",
            "reasoning_summary": "No tools needed for identity query."
        })
    elif "multi-tool_test" in content.lower():
        # D. Multi-tool
        return json.dumps({
            "requires_tools": True,
            "selections": [
                {
                    "tool_name": "document_reader",
                    "confidence": 0.9,
                    "reason": "load data",
                    "required_inputs": {"file_path": "data.csv"}
                },
                {
                    "tool_name": "python_interpreter",
                    "confidence": 0.9,
                    "reason": "process data",
                    "required_inputs": {"code": "df.mean()"}
                }
            ],
            "fallback_strategy": "Abort",
            "reasoning_summary": "Load then process data."
        })
    elif "hallucinated_tool" in content.lower():
        # F. Unknown tool
        return json.dumps({
             "requires_tools": True,
             "selections": [
                 {
                     "tool_name": "magic_crystal_ball",
                     "confidence": 0.99,
                     "reason": "Just magical.",
                     "required_inputs": {}
                 }
             ],
             "fallback_strategy": "Abort",
             "reasoning_summary": "Hallucinated."
        })
    elif "fail" in content.lower():
        # E. Malformed
        return "I am not returning JSON today."

    return "{}"


def run_verification():
    print("=== TONY TOOL ROUTING VERIFICATION (PART 8D) ===\n")
    
    with patch("apps.backend.tools.tool_router.run_llm_inference", side_effect=mock_inference):
        
        # A. Search
        print("\n[TEST A] Web Search Routing")
        res_a = route_tools_for_task("What is the latest news?", {})
        assert res_a.requires_tools is True
        assert res_a.selections[0].tool_name == "web_search"
        print("Test A Passed")
        
        # B. Document
        print("\n[TEST B] Document Reader Routing")
        res_b = route_tools_for_task("Please read summary.pdf", {})
        assert res_b.requires_tools is True
        assert res_b.selections[0].tool_name == "document_reader"
        print("Test B Passed")
        
        # C. Direct
        print("\n[TEST C] Direct Answer (No Tool)")
        res_c = route_tools_for_task("Who are you?", {})
        assert res_c.requires_tools is False
        assert len(res_c.selections) == 0
        print("Test C Passed")
        
        # D. Multi-tool
        print("\n[TEST D] Multi-Tool Routing")
        res_d = route_tools_for_task("multi-tool_test", {})
        assert res_d.requires_tools is True
        assert len(res_d.selections) == 2
        print("Test D Passed")
        
        # F. Unknown tool rejection
        print("\n[TEST F] Hallucinated Tool Rejection")
        res_f = route_tools_for_task("use hallucinated_tool", {})
        assert res_f.requires_tools is False # Became False because choices dropped
        assert len(res_f.selections) == 0
        print("Test F Passed")
        
        # E. Invalid format
        print("\n[TEST E] Malformed Output Fallback")
        res_e = route_tools_for_task("FAIL", {})
        assert res_e.requires_tools is False
        print("Test E Passed")
        
        print("\n=== RAW DECISION DUMP (Multi-Tool) ===")
        print(res_d.model_dump_json(indent=2))

    print("\n=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    run_verification()
