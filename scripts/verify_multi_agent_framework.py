import os
import sys
import json
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.agents.multi_agent_orchestrator import run_multi_agent_workflow
from apps.backend.schemas.agent import SpecialistResult

def mock_inference(messages, model):
    content = messages[-1]["content"] if isinstance(messages, list) else messages
    
    # 1. Routing phase mock
    if "Delegation Router" in str(messages):
        if "Unknown Task" in content:
            return "NO_JSON_JUST_NOISE" # Test fallback (E)
        if "Code and Research" in content:
            return json.dumps([
                {"specialist_id": "coding_expert", "reason": "Write code", "priority": 2},
                {"specialist_id": "research_expert", "reason": "Get facts", "priority": 1}
            ])
            
    # 2. Execution phase mock
    if "Coding Specialist" in str(messages):
        return "def hello(): print('world')"
    if "Research Specialist" in str(messages):
        return "Fact: Python is a language."
    if "Writing Specialist" in str(messages):
        return "Here is a beautifully written poem about nothing."
        
    # 3. Aggregation phase mock
    if "Coordinator" in str(messages):
        return "Final Answer: The research says python is a language, and the code prints world."

    return "Default output"

def run_verification():
    print("=== TONY MULTI-AGENT SUB-SYSTEM VERIFICATION (PART 8L) ===\n")
    
    with patch("apps.backend.agents.delegation_router.run_llm_inference", side_effect=mock_inference), \
         patch("apps.backend.agents.subagent_executor.run_llm_inference", side_effect=mock_inference), \
         patch("apps.backend.agents.multi_agent_orchestrator.run_llm_inference", side_effect=mock_inference):

        # A, B, C, D: Correct specialists, Multiple exec, Aggregation, Ranking prioritized
        print("[TEST A, B, C, D] Standard Multi-Agent Delegation & Synthesis")
        result = run_multi_agent_workflow("Code and Research Task")
        
        assert "Final Answer:" in result["final_output"], "Failed aggregation"
        res_list = result["specialist_results"]
        # Ensure it was ranked: research (priority 1) first, coding (priority 2) second
        assert len(res_list) == 2
        assert res_list[0]["specialist_id"] == "research_expert"
        assert res_list[1]["specialist_id"] == "coding_expert"
        assert res_list[0]["output"] == "Fact: Python is a language."
        print("Tests A, B, C, D Passed\n")
        
        # E. Unknown tasks fallback safely (expecting writing_expert)
        print("[TEST E & F] Fallback Routing & Schema Structuring")
        fallback_res = run_multi_agent_workflow("Unknown Task String")
        fallback_list = fallback_res["specialist_results"]
        assert len(fallback_list) == 1
        assert fallback_list[0]["specialist_id"] == "writing_expert"
        assert fallback_list[0]["confidence"] >= 0.5 # Schema ensures float
        print("Tests E & F Passed\n")
        
        print("\n=== RAW MULTI-AGENT TRACE DUMP (Test A) ===")
        print(json.dumps(result, indent=2))

    print("\n=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    run_verification()
