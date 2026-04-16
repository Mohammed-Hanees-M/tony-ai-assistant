import os
import sys
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.agent.autonomous_loop import run_autonomous_task
from apps.backend.schemas.plan import Plan, PlanStep
from apps.backend.schemas.tool import ToolRoutingDecision, ToolExecutionTrace, ToolExecutionResult

def mock_plan(goal: str, *args, **kwargs):
    if "Recover" in goal:
        return Plan(user_goal=goal, title="Recovery", steps=[PlanStep(id="r1", title="Recovery Step", description="Fix issue", order_index=1)])
    elif "Infinite" in goal:
        return Plan(user_goal=goal, title="Infinite Action", steps=[PlanStep(id="inf", title="Fail always", description="x", order_index=1)])
    return Plan(user_goal=goal, title="Standard Plan", steps=[
        PlanStep(id="p1", title="Step 1", description="Do A", order_index=1),
        PlanStep(id="p2", title="Step 2", description="Do B", order_index=2)
    ])

def mock_route_tools(description: str, *args, **kwargs):
    return ToolRoutingDecision(requires_tools=True) # Always true for tests to hit executor

def mock_execute_tool(decision, *args, **kwargs):
    global MOCK_EXEC_COUNT
    MOCK_EXEC_COUNT += 1
    
    if getattr(sys, "INFINITE_MODE", False):
        return ToolExecutionTrace(results=[ToolExecutionResult(tool_name="test", success=False)], overall_success=False)
        
    if MOCK_EXEC_COUNT == 2: # Fail the second step to test replanning
        return ToolExecutionTrace(results=[ToolExecutionResult(tool_name="test", success=False)], overall_success=False)
        
    return ToolExecutionTrace(results=[ToolExecutionResult(tool_name="test", success=True)], overall_success=True)

MOCK_EXEC_COUNT = 0

def run_verification():
    print("=== TONY AUTONOMOUS AGENT VERIFICATION (PART 8H) ===\n")
    
    with patch("apps.backend.agent.autonomous_loop.generate_execution_plan", side_effect=mock_plan), \
         patch("apps.backend.agent.autonomous_loop.route_tools_for_task", side_effect=mock_route_tools), \
         patch("apps.backend.agent.autonomous_loop.execute_tool_plan", side_effect=mock_execute_tool):
         
        global MOCK_EXEC_COUNT
        MOCK_EXEC_COUNT = 0
        setattr(sys, "INFINITE_MODE", False)
        
        # A, B, C, D, F -> Multi-step, updates correctly, fail triggers replan, completes, trace preserved
        print("\n[TEST A, B, C, D, F] Full Autonomous Recovery Loop")
        state_full = run_autonomous_task("Build API")
        
        assert state_full.status == "success"
        assert len(state_full.completed_steps) == 2 # p1, r1
        assert len(state_full.execution_history) == 3 # p1 success, p2 fail, r1 success
        print("Tests A, B, C, D, F Passed.")
        
        # E -> Terminate on max iterations safety cap
        MOCK_EXEC_COUNT = 0
        setattr(sys, "INFINITE_MODE", True)
        
        print("\n[TEST E] Max Iteration Safety Cap")
        state_inf = run_autonomous_task("Infinite Loop Task", max_iterations=3)
        assert state_inf.status == "max_iterations"
        assert state_inf.iteration_count > 3
        print("Test E Passed.")
        
        print("\n=== RAW FINAL STATE DUMP (Full Loop) ===")
        print(state_full.model_dump_json(indent=2))

    print("\n=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    run_verification()
