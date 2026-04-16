from typing import Optional
from apps.backend.schemas.agent import AutonomousTaskState, ApprovalCheckpoint, ApprovalDecision
from apps.backend.schemas.plan import PlanStep
from apps.backend.schemas.tool import ToolRoutingDecision

# Configurable Risk Categories
HIGH_RISK_TOOLS = [
    "run_os_command", "shell_exec", 
    "delete_file", "write_file", 
    "execute_sql", "drop_table",
    "deploy_to_production", "send_email"
]

HIGH_RISK_KEYWORDS = [
    "delete", "remove", "drop", "destroy", "format",
    "sudo", "rm -rf", "deploy", "send", "write"
]

def requires_human_approval(step: PlanStep, routing_decision: ToolRoutingDecision) -> tuple[bool, str, str]:
    """Returns (requires_approval, risk_level, reason)"""
    
    # Check tool registry matches
    for selection in routing_decision.selections:
        if selection.tool_name in HIGH_RISK_TOOLS:
            return True, "high", f"Use of high risk tool: {selection.tool_name}"
            
    # Check keywords in step description
    desc_lower = step.description.lower()
    for kw in HIGH_RISK_KEYWORDS:
        if kw in desc_lower:
            return True, "medium", f"High risk keyword detected in step description: '{kw}'"
            
    return False, "low", ""

def process_approval_response(task_state: AutonomousTaskState, decision: ApprovalDecision):
    if not task_state.pending_checkpoint:
        print("[APPROVAL ENGINE] No pending checkpoint to process.")
        return
        
    checkpoint = task_state.pending_checkpoint
    checkpoint.decision = decision
    
    # Store in audit trail
    task_state.audit_trail.append(checkpoint)
    task_state.pending_checkpoint = None
    
    if not decision.approved:
        print("[APPROVAL ENGINE] Human REJECTED the pending step.")
        task_state.status = "fatal_failure"
    else:
        task_state.approved_steps.append(checkpoint.pending_step.id)
        if decision.modified_step:
            print("[APPROVAL ENGINE] Human MODIFIED the pending step.")
            # Replace the step in the plan
            for i, step in enumerate(task_state.current_plan.steps):
                if step.id == checkpoint.pending_step.id:
                    task_state.current_plan.steps[i] = decision.modified_step
                    break
        else:
            print("[APPROVAL ENGINE] Human APPROVED the pending step.")
            
        task_state.status = "running"
        print("[APPROVAL ENGINE] Resuming task execution.")
