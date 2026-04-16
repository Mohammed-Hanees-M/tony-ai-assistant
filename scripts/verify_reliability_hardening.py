import os
import sys
import json
import time
from unittest.mock import patch, MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.utils.json_parser import safe_parse_json, extract_json_block
from apps.backend.agent.autonomous_loop import run_autonomous_task
from apps.backend.schemas.agent import AutonomousTaskState
from apps.backend.schemas.plan import Plan, PlanStep

def run_verification():
    print("=== TONY RELIABILITY HARDENING VERIFICATION (PART 8V) ===\n")
    
    # 1. JSON Parser Tests
    print("[TEST 1] JSON Parser: Noisy Background Extraction")
    noisy_input = "Here is the result: {'key': 'value'} - hope it helps!"
    parsed = safe_parse_json(noisy_input)
    assert parsed.get("key") == "value"
    
    print("[TEST 2] JSON Parser: Malformed Fallback")
    malformed = "{'key': 'value', broken...}"
    parsed_fallback = safe_parse_json(malformed, fallback={"safe": True})
    assert parsed_fallback["safe"] == True
    print("Test 1-2 Passed (Safe Parsing)\n")

    # 2. Re-planning Loop Prevention
    print("[TEST 3] Re-planning Loop: Infinite Retry Prevention")
    
    # Mock planner to always return a plan with a failing step
    mock_plan = Plan(
        id="loop_plan",
        user_goal="Infinite Task",
        title="Failing Strategy",
        steps=[PlanStep(id="st1", title="Constant Failure", description="Will fail", order_index=1)]
    )
    
    # Mock executor to always report failure
    mock_trace = MagicMock()
    mock_trace.overall_success = False
    
    with patch("apps.backend.agent.autonomous_loop.generate_execution_plan", return_value=mock_plan), \
         patch("apps.backend.agent.autonomous_loop.execute_tool_plan", return_value=mock_trace), \
         patch("apps.backend.agent.autonomous_loop.route_tools_for_task", return_value=MagicMock(requires_tools=True)):
        
        state = run_autonomous_task("Break Tony", max_replants=2)
        
        # Should stop after 3 attempts (initial + 2 replans)
        assert state.replan_count == 3
        assert state.status == "fatal_failure"
        assert len(state.failure_history) == 3
        print("  -> Correctly aborted after reaching max_replants limit.")
        print("  -> Failure history persisted across all 3 attempts.")
        
    print("Test 3 Passed (Loop Prevention)\n")

    print("\n=== RELIABILITY TRACE DUMP (Failure History) ===")
    print(json.dumps(state.failure_history, indent=2))

    print("\n=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    run_verification()
