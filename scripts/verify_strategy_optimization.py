import os
import sys
import json
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.schemas.tool import ToolExecutionTrace, ToolExecutionResult
from apps.backend.planning.strategy_optimizer import analyze_and_optimize_strategy, get_preferred_strategy, _GLOBAL_STRATEGY_PROFILES

def mock_inference(messages, model):
    content = messages[-1]["content"]
    
    if "Research Task Fast" in content:
        return json.dumps({
            "context_pattern": "Research",
            "workflow_pattern": "web_search_fast",
            "notes": "Direct fast search."
        })
    elif "Research Task Slow" in content:
        return json.dumps({
            "context_pattern": "Research",
            "workflow_pattern": "web_search_slow",
            "notes": "Slow thorough search."
        })
    elif "Fail Workflow" in content:
        return json.dumps({
            "context_pattern": "Research",
            "workflow_pattern": "broken_workflow",
            "notes": "Always fails."
        })
    elif "Noise Test" in content:
        return json.dumps({
            "context_pattern": "Noise",
            "workflow_pattern": "random_actions",
            "notes": "Just 1 time."
        })

    return "{}"

def run_verification():
    print("=== TONY STRATEGY OPTIMIZATION VERIFICATION (PART 8G) ===\n")
    
    # Initialize global state to clean test
    _GLOBAL_STRATEGY_PROFILES.clear()
    
    with patch("apps.backend.planning.strategy_optimizer.run_llm_inference", side_effect=mock_inference):
        
        # A & F. Fast workflow 1st time -> No preferred yet (Noise Filtering)
        t_fast_1 = ToolExecutionTrace(results=[ToolExecutionResult(tool_name="web_search", success=True, execution_time_ms=100)])
        analyze_and_optimize_strategy("Research Task Fast", t_fast_1, True)
        
        # Check F
        pref_none = get_preferred_strategy("Research")
        assert pref_none is None, "Should not optimize until usage >= 2"
        print("Test F Passed (Noise filter block)")
        
        # Fast workflow 2nd time -> Becomes preferred
        analyze_and_optimize_strategy("Research Task Fast", t_fast_1, True)
        
        # Check A & B & E
        pref_fast = get_preferred_strategy("Research")
        assert pref_fast is not None
        assert pref_fast.workflow_pattern == "web_search_fast"
        assert pref_fast.usage_count == 2
        assert pref_fast.avg_latency_ms == 100.0
        assert pref_fast.success_rate == 1.0
        print("Test A, B, E Passed (Profile created and returned via getter)")
        
        # C & D. Slow workflow 2 times, highly successful but slower
        t_slow = ToolExecutionTrace(results=[ToolExecutionResult(tool_name="web_search", success=True, execution_time_ms=500)])
        analyze_and_optimize_strategy("Research Task Slow", t_slow, True)
        analyze_and_optimize_strategy("Research Task Slow", t_slow, True) # 2 times -> valid profile
        
        # Fast should still be preferred due to lower latency
        pref_check = get_preferred_strategy("Research")
        assert pref_check.workflow_pattern == "web_search_fast"
        
        # Introduce failures to Fast workflow
        t_fail = ToolExecutionTrace(results=[ToolExecutionResult(tool_name="web_search", success=False, execution_time_ms=50)])
        analyze_and_optimize_strategy("Research Task Fast", t_fail, False) # Usage 3, Success 66%
        analyze_and_optimize_strategy("Research Task Fast", t_fail, False) # Usage 4, Success 50%
        
        # Now Slow should be preferred
        pref_shifted = get_preferred_strategy("Research")
        assert pref_shifted.workflow_pattern == "web_search_slow"
        print("Test C & D Passed (Ranking logic demotes failing and promotes stable/slow)")
        
        print("\n=== RAW STRATEGY PROFILES DATABASE DUMP ===")
        for ctx, profiles in _GLOBAL_STRATEGY_PROFILES.items():
            for p in profiles:
                print(p.model_dump_json(indent=2))

    print("\n=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    run_verification()
