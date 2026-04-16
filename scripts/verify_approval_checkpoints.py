import os
import sys
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.agent.autonomous_loop import run_autonomous_task
from apps.backend.schemas.plan import Plan, PlanStep
from apps.backend.schemas.tool import ToolRoutingDecision, ToolExecutionTrace, ToolExecutionResult, ToolSelection
from apps.backend.schemas.agent import ApprovalDecision
from apps.backend.agent.approval_engine import process_approval_response

def mock_plan(goal: str, *args, **kwargs):
    if "Risky" in goal:
        return Plan(user_goal=goal, title="Risky Plan", steps=[
            PlanStep(id="s1", title="Step 1", description="delete data", order_index=1),
            PlanStep(id="s2", title="Step 2", description="finish", order_index=2)
        ])
    return Plan(user_goal=goal, title="Safe Plan", steps=[
        PlanStep(id="s1", title="Step 1", description="read data", order_index=1)
    ])

def mock_route_tools(description: str, *args, **kwargs):
    if "delete" in description:
        return ToolRoutingDecision(requires_tools=True, selections=[ToolSelection(tool_name="run_os_command", reason="Delete", required_inputs={})])
    return ToolRoutingDecision(requires_tools=False)

def mock_execute_tool(decision, *args, **kwargs):
    return ToolExecutionTrace(results=[ToolExecutionResult(tool_name="test", success=True)], overall_success=True)

def run_verification():
    print("=== TONY APPROVAL / OVERSIGHT VERIFICATION (PART 8I) ===\n")
    
    with patch("apps.backend.agent.autonomous_loop.generate_execution_plan", side_effect=mock_plan), \
         patch("apps.backend.agent.autonomous_loop.route_tools_for_task", side_effect=mock_route_tools), \
         patch("apps.backend.agent.autonomous_loop.execute_tool_plan", side_effect=mock_execute_tool):

        # A. Safe actions proceed without approval
        print("\n[TEST A] Safe Workflow")
        state_safe = run_autonomous_task("Safe")
        assert state_safe.status == "success"
        assert state_safe.pending_checkpoint is None
        print("Test A Passed")

        # B. Risky actions trigger pause
        print("\n[TEST B] Risky Workflow Pause")
        state_risk = run_autonomous_task("Risky")
        assert state_risk.status == "awaiting_approval"
        assert state_risk.pending_checkpoint is not None
        assert state_risk.pending_checkpoint.risk_level == "high"
        
        # Test Audit Trail exists
        assert len(state_risk.audit_trail) == 0 # Not audited until decided
        print("Test B Passed")
        
        # C. Approve resumes execution
        print("\n[TEST C & F] Approve & Resume & Audit Trail")
        # Process approval
        decision = ApprovalDecision(approved=True, notes="Looks safe.")
        process_approval_response(state_risk, decision)
        
        assert state_risk.status == "running"
        assert len(state_risk.audit_trail) == 1
        
        # Resume the loop
        state_risk = run_autonomous_task(state_risk.user_goal, state=state_risk)
        assert state_risk.status == "success"
        print("Test C & F Passed")

        # D. Reject aborts safely
        print("\n[TEST D] Reject Aborts")
        state_reject = run_autonomous_task("Risky")
        process_approval_response(state_reject, ApprovalDecision(approved=False))
        assert state_reject.status == "fatal_failure"
        print("Test D Passed")
        
        # E. Modify changes step
        print("\n[TEST E] Modify Changes Step")
        state_modify = run_autonomous_task("Risky")
        modified_step = PlanStep(id=state_modify.pending_checkpoint.pending_step.id, title="Step 1 Mod", description="read data instead", order_index=1)
        process_approval_response(state_modify, ApprovalDecision(approved=True, modified_step=modified_step))
        
        assert state_modify.status == "running"
        assert state_modify.current_plan.steps[0].description == "read data instead"
        print("Test E Passed")
        
        print("\n=== RAW AUDIT TRAIL DUMP (From Test C) ===")
        print(state_risk.audit_trail[0].model_dump_json(indent=2))

    print("\n=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    run_verification()
