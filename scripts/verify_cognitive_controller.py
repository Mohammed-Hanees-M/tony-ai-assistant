import os
import sys
import json
import time
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.cognition.cognitive_controller import get_brain_controller

def mock_inference(messages, model):
    user_content = messages[1]["content"] if len(messages) > 1 else ""
    
    # A. Simple
    if "Simple" in user_content:
        return json.dumps({
            "required_modules": ["memory"],
            "execution_order": [
                {"module_name": "memory", "description": "Quick lookup", "order_index": 1}
            ],
            "reasoning_depth": "shallow",
            "estimated_complexity": "low",
            "risk_level": "low"
        })
        
    # B. Complex
    if "Complex" in user_content:
        return json.dumps({
            "required_modules": ["memory", "reasoning", "planner"],
            "execution_order": [
                {"module_name": "memory", "description": "Base context", "order_index": 1},
                {"module_name": "planner", "description": "Goal breakdown", "order_index": 2},
                {"module_name": "reasoning", "description": "Step logic", "order_index": 3}
            ],
            "estimated_complexity": "high"
        })
        
    # C. Risky
    if "Risky" in user_content:
        return json.dumps({
            "required_modules": ["world_model", "tool_execution"],
            "execution_order": [
                {"module_name": "world_model", "description": "Check risk", "order_index": 1},
                {"module_name": "tool_execution", "description": "Run", "order_index": 2}
            ],
            "risk_level": "high"
        })

    # D. Budget
    if "Budget" in user_content:
        return json.dumps({
            "required_modules": ["memory", "reasoning"],
            "execution_order": [
                {"module_name": "memory", "description": "1", "order_index": 1},
                {"module_name": "reasoning", "description": "2", "order_index": 2}
            ],
            "budgets": {"max_latency_ms": 10} # Tiny budget
        })

    return "{}"

def run_verification():
    print("=== TONY COGNITIVE CONTROLLER VERIFICATION (PART 8S) ===\n")
    brain = get_brain_controller()
    
    with patch("apps.backend.cognition.cognitive_controller.run_llm_inference", side_effect=mock_inference):
        
        # Test A: Simple
        print("[TEST A] Simple query -> Minimal pipeline")
        trace_a = brain.run_cognitive_pipeline("Simple hello", {})
        assert len(trace_a.plan.required_modules) == 1
        assert "memory" in trace_a.plan.required_modules
        print("Test A Passed\n")
        
        # Test B & E: Complex + Dynamic Ordering
        print("[TEST B & E] Complex query -> Order enforcement")
        trace_b = brain.run_cognitive_pipeline("Complex logic task", {})
        order = [s.module_name for s in sorted(trace_b.plan.execution_order, key=lambda x: x.order_index)]
        assert order == ["memory", "planner", "reasoning"]
        assert trace_b.plan.estimated_complexity == "high"
        print("Tests B & E Passed\n")
        
        # Test C: Risky
        print("[TEST C] Risky query -> Safety checks")
        trace_c = brain.run_cognitive_pipeline("Risky system command", {})
        assert trace_c.plan.risk_level == "high"
        assert "world_model" in trace_c.plan.required_modules
        print("Test C Passed\n")
        
        # Test D: Budget
        print("[TEST D] Budget Enforcement (Latency)")
        # Artificially delaying execution to trigger timeout
        with patch("time.time", side_effect=[0, 0, 0, 0.5, 1, 1.5, 2, 2.5]): 
             # Mock times: 0 (start), 0 (plan), 0 (check 1st mod), 0.5 (check 2nd mod)
             # Wait, let's just use a real delay if needed or simpler mock
             pass
        
        # Simpler way to test budget logic without complex time mocking:
        # We'll just rely on the trace.skipped_modules appearing if latency is exceeded.
        with patch("time.time", side_effect=[100, 100, 100, 200, 200, 200]): # 100s start...
             trace_d = brain.run_cognitive_pipeline("Budget test", {})
             # Since it's tiny budget (10ms) and time jumps 100s, it should skip.
             assert len(trace_d.skipped_modules) > 0
             assert trace_d.skipped_modules[0]["reason"] == "latency_budget_exhausted"
        print("Test D Passed\n")
        
        print("\n=== RAW COGNITIVE TRACE DUMP (Test B) ===")
        print(json.dumps(trace_b.model_dump(), indent=2))

    print("\n=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    run_verification()
