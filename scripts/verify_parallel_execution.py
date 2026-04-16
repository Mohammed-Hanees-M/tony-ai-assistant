import os
import sys
import json
import time
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.agents.multi_agent_orchestrator import run_multi_agent_workflow
from apps.backend.agents.parallel_executor import execute_specialists_parallel
from apps.backend.schemas.agent import SpecialistResult

def mock_inference(messages, model):
    content = messages[-1]["content"] if isinstance(messages, list) else messages
    if "Delegation Router" in str(messages):
         return json.dumps([
            {"specialist_id": "coding_expert", "reason": "Write code", "priority": 3},
            {"specialist_id": "research_expert", "reason": "Get facts", "priority": 1},
            {"specialist_id": "finance_expert", "reason": "Do math", "priority": 2} # Fails
        ])
    if "Coordinator" in str(messages):
        return "Final Aggregated Parallel Data"
    return "Default output"

def mock_execute(spec, query, model):
    if spec.id == "finance_expert":
        time.sleep(0.1)
        raise ValueError("Simulated isolated failure")
    if spec.id == "coding_expert":
        time.sleep(1.0) # Will exceed local test timeout of 0.5s
    else:
        time.sleep(0.2) # Fast normal path
        
    return SpecialistResult(
        specialist_id=spec.id, subtask=query, output=f"Output from {spec.id}", confidence=0.9
    )

def test_wrapper(assignments, query, model):
    return execute_specialists_parallel(assignments, query, model, timeout_sec=0.5)

def run_verification():
    print("=== TONY PARALLEL EXECUTION VERIFICATION (PART 8M) ===\n")
    
    with patch("apps.backend.agents.delegation_router.run_llm_inference", side_effect=mock_inference), \
         patch("apps.backend.agents.multi_agent_orchestrator.run_llm_inference", side_effect=mock_inference), \
         patch("apps.backend.agents.parallel_executor.execute_specialist_task", side_effect=mock_execute), \
         patch("apps.backend.agents.multi_agent_orchestrator.execute_specialists_parallel", side_effect=test_wrapper):

        print("[TEST] Launching Orchestrator...")
        start_time = time.time()
        result = run_multi_agent_workflow("Do everything concurrently")
        total_time = time.time() - start_time
        
        # B. Total runtime less than sequential sum (0.2 + 0.1 + 1.0 > 0.5)
        print(f"[METRIC] Total parallel execution time: {total_time:.2f}s")
        assert total_time < 0.9, f"Took {total_time}s - Threading failed!"
        
        # A, C: Results exist and ordering is preserved (Priority 1, 2, 3)
        res_list = result["specialist_results"]
        assert len(res_list) == 3
        assert res_list[0]["specialist_id"] == "research_expert" # priority 1
        assert res_list[1]["specialist_id"] == "finance_expert"  # priority 2
        assert res_list[2]["specialist_id"] == "coding_expert"   # priority 3
        
        # E. Failure Isolation Works
        assert res_list[1]["metadata"]["failed"] is True
        assert "Simulated isolated failure" in res_list[1]["output"]
        
        # D. Timeout Handling Works
        assert res_list[2]["metadata"]["timeout_occurred"] is True
        assert "timed out" in res_list[2]["output"]
        
        # Normal trace works
        assert res_list[0]["output"] == "Output from research_expert"
        assert res_list[0]["metadata"]["timeout_occurred"] is False
        
        print("\nAll Tests Successfully Bound & Evaluated!")
        print("\n=== RAW MULTI-AGENT METRICS DUMP (Metrics capture correctly) ===")
        print(json.dumps(result["specialist_results"], indent=2))

    print("\n=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    run_verification()
