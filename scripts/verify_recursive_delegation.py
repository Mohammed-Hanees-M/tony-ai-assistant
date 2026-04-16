import os
import sys
import json
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.agents.recursive_delegator import run_recursive_delegation

def mock_inference(messages, model):
    content = messages[0]["content"]
    user_content = messages[1]["content"] if len(messages) > 1 else ""
    
    if "Does this task require delegating to multiple sub-specialists" in content:
        if "Flat" in user_content:
            return "false"
        if "Recursive" in user_content:
             return "true"
        return "false"
        
    if "Delegation Router" in content:
        if "Deep" in user_content:
             return json.dumps([{"specialist_id": "planning_expert", "priority": 1}])
        return json.dumps([{"specialist_id": "coding_expert", "priority": 1}])
        
    if "Synthesize child results" in content:
        return "Aggregated Tree Result."
        
    return "Base flat execution simulated output."
    

def run_verification():
    print("=== TONY RECURSIVE DELEGATION VERIFICATION (PART 8O) ===\n")
    
    with patch("apps.backend.agents.recursive_delegator.run_llm_inference", side_effect=mock_inference), \
         patch("apps.backend.agents.delegation_router.run_llm_inference", side_effect=mock_inference), \
         patch("apps.backend.agents.subagent_executor.run_llm_inference", side_effect=mock_inference):

        # A, B, C: Manager spawns child and aggregates output
        print("[TEST A, B, C] Proper Sub-Agent Spawn and Tree Trace")
        res1 = run_recursive_delegation("Recursive Query", "planning_expert")
        assert res1.children, "Did not decompose!"
        assert res1.children[0].specialist_id == "coding_expert", "Wrong child delegation"
        assert res1.result.output == "Aggregated Tree Result.", "Did not aggregate upward!"
        assert res1.result.metadata.get("is_manager_aggregate") == True
        print("Tests A, B, C Passed\n")
        
        # D: Depth Limits Enforced
        print("[TEST D] Depth Limit Protection")
        res2 = run_recursive_delegation("Recursive Deep", "planning_expert", max_depth=1)
        assert len(res2.children[0].children) == 0, "Violated max depth constraint!"
        assert res2.children[0].result.output == "Base flat execution simulated output."
        print("Test D Passed\n")
        
        # F: Flat Tasks bypass safely
        print("[TEST F] Flat Delegation Exit")
        res3 = run_recursive_delegation("Flat Query", "planning_expert")
        assert len(res3.children) == 0, "Wrongly decomposed flat task"
        print("Test F Passed\n")

        print("\n=== RAW DELEGATION TREE DUMP ===")
        print(json.dumps(res1.model_dump(), indent=2))

    print("\n=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    run_verification()
