import time
from typing import Optional
from apps.backend.schemas.agent import AutonomousTaskState, ApprovalCheckpoint
from apps.backend.schemas.plan import PlanStep
from apps.backend.planning.planner import generate_execution_plan
from apps.backend.tools.tool_router import route_tools_for_task
from apps.backend.tools.tool_executor import execute_tool_plan
from apps.backend.agent.approval_engine import requires_human_approval

def run_autonomous_task(user_goal: str, state: Optional[AutonomousTaskState] = None, max_iterations: int = 10, max_replants: int = 3, stop_on_fail: bool = False, notification_service=None, model: str = "phi3") -> AutonomousTaskState:
    if not state:
        print(f"\n[AGENT] Starting autonomous task loop for goal: '{user_goal}'")
        state = AutonomousTaskState(user_goal=user_goal, status="running")
    else:
        print(f"\n[AGENT] Resuming autonomous task loop for goal: '{user_goal}'")
        
    if not state.current_plan:
        print(f"[AGENT] Generating Initial Plan...")
        state.current_plan = generate_execution_plan(user_goal, model=model)

    
    while state.status == "running":
        state.iteration_count += 1
        print(f"\n[AGENT] --- Iteration {state.iteration_count} ---")
        
        # 1. Guardrail max iterations
        if state.iteration_count > max_iterations:
            print("[AGENT] Maximum iterations reached. Forcing failure.")
            state.status = "max_iterations"
            break
            
        # 2. Evaluate current state & select next step
        next_step: Optional[PlanStep] = None
        for step in state.current_plan.steps:
            if step.id not in state.completed_steps and step.id not in state.failed_steps:
                next_step = step
                break
                
        if not next_step:
            if not state.failed_steps:
                print("[AGENT] All steps completed successfully.")
                state.status = "success"
                if notification_service:
                    notification_service.notify_task_completed(state.task_id, state.user_goal)
            else:
                print("[AGENT] No pending steps, but some failed previously. Halting.")
                state.status = "fatal_failure"
                if notification_service:
                    notification_service.notify_task_failed(state.task_id, state.user_goal, "Failed to complete necessary steps.")
            break
            
        print(f"[AGENT] Next Step Selected: {next_step.title}")
        
        # 3. Route tools
        routing_decision = route_tools_for_task(next_step.description, context={"goal": state.user_goal}, model=model)

        
        # OVERSIGHT CHECKPOINT: Do we need human approval?
        if next_step.id not in state.approved_steps:
            req_approval, risk_level, reason = requires_human_approval(next_step, routing_decision)
            if req_approval:
                print(f"[AGENT OVERSIGHT] Risk detected ({risk_level}): {reason}")
                state.pending_checkpoint = ApprovalCheckpoint(
                    task_id=state.task_id,
                    reason=reason,
                    pending_step=next_step,
                    risk_level=risk_level
                )
                state.status = "awaiting_approval"
                print("[AGENT] Pausing execution to await human approval.")
                if notification_service:
                    notification_service.notify_approval_required(state.task_id, state.user_goal, risk_level, reason)
                break
        
        # 4. Execute
        trace = execute_tool_plan(routing_decision)
        state.execution_history.append(trace)
        
        # 5. Verify result
        if trace.overall_success or not routing_decision.requires_tools:
            print(f"[AGENT] Step '{next_step.title}' completed successfully.")
            state.completed_steps.append(next_step.id)
            next_step.status = "completed"
        else:
            print(f"[AGENT] Step '{next_step.title}' failed.")
            state.failed_steps.append(next_step.id)
            next_step.status = "failed"
            
            if stop_on_fail:
                state.status = "fatal_failure"
                if notification_service:
                    notification_service.notify_task_failed(state.task_id, state.user_goal, f"Hard stop triggered by failure in step: {next_step.title}")
                break
                
                break
                
            # 6. Re-planning hook with loop prevention
            state.replan_count += 1
            
            # Persist failure context FIRST
            state.failure_history.append({
                "replan_index": state.replan_count,
                "failed_step": next_step.title,
                "reason": "Execution trace reported failure",
                "timestamp": time.time()
            })

            if state.replan_count > max_replants:
                print(f"[AGENT] Max re-plan limit ({max_replants}) reached. Escalating to fatal failure.")
                state.status = "fatal_failure"
                if notification_service:
                    notification_service.notify_task_failed(state.task_id, state.user_goal, "Repeated failures exceeded recovery threshold.")
                break

            print(f"[AGENT] Invoking Re-Planner (Attempt {state.replan_count}) to map fallback strategy...")
            new_plan = generate_execution_plan(f"Recover from failure: {next_step.description}. Context: Previous attempts failed for this reason.", model=model)

            state.current_plan = new_plan
            state.failed_steps.clear() # Clear failure to run new plan
            
            
            
    if state.status != "awaiting_approval":
        print(f"\n[AGENT] Task Loop Terminated. Final Status: {state.status}")
    return state
