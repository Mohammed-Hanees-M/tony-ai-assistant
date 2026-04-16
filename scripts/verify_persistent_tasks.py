import os
import sys
import time
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.database.base import Base
from apps.backend.agent.task_repository import TaskRepository
from apps.backend.agent.task_worker import run_task_worker_loop
from apps.backend.agent.autonomous_loop import run_autonomous_task
from apps.backend.schemas.agent import AutonomousTaskState
from apps.backend.schemas.plan import Plan, PlanStep
from apps.backend.database.models.task_record import AutonomousTaskRecord
from apps.backend.schemas.tool import ToolRoutingDecision, ToolExecutionTrace, ToolExecutionResult

def mock_plan(goal: str, *args, **kwargs):
    return Plan(user_goal=goal, title="Dumb Plan", steps=[
        PlanStep(id="s1", title="S1", description="Exec", order_index=1)
    ])

def mock_route(*args, **kwargs):
    return ToolRoutingDecision(requires_tools=False)

def mock_exec(*args, **kwargs):
    return ToolExecutionTrace()

def run_verification():
    print("=== TONY PERSISTENT TASKS VERIFICATION (PART 8J) ===\n")
    
    # 0. Set up purely transient DB exclusively for this verification bounds
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    repo = TaskRepository(db)
    
    with patch("apps.backend.agent.autonomous_loop.generate_execution_plan", side_effect=mock_plan), \
         patch("apps.backend.agent.autonomous_loop.route_tools_for_task", side_effect=mock_route), \
         patch("apps.backend.agent.autonomous_loop.execute_tool_plan", side_effect=mock_exec):
         
        # TEST A: Task state persists to DB
        print("\n[TEST A] Persistent State Creation")
        mock_state = AutonomousTaskState(user_goal="Test Goal", status="initialized")
        db_record = repo.save_task_state(mock_state)
        assert db_record.task_id == mock_state.task_id
        assert db_record.status == "initialized"
        print("Test A Passed")

        # TEST C: Scheduled tasks wait until eligible
        print("\n[TEST C] Scheduled Task Constraints")
        future_state = AutonomousTaskState(user_goal="Future Goal", status="pending")
        repo.save_task_state(future_state, scheduled_for=time.time() + 1000)
        
        # Verify worker does NOT claim the future scheduled state
        claimed = repo.claim_task_for_worker("test_worker")
        assert claimed is not None
        assert claimed.user_goal == "Test Goal", "Worker bypassed schedule constraint"
        
        # Release lock so the worker loop can pick it up
        check_rec = db.query(AutonomousTaskRecord).filter(AutonomousTaskRecord.task_id == mock_state.task_id).first()
        check_rec.status = "pending"
        check_rec.last_heartbeat = None
        db.commit()
        
        print("Test C Passed")

        print("\n[TEST B & F] Worker Processes Queued Tasks")
        # Ensure that the worker loop evaluates & finishes the queued logic properly
        run_task_worker_loop(db, max_loops=2)
        
        # Check DB State for Test Goal -> It should be success
        check_rec = db.query(AutonomousTaskRecord).filter(AutonomousTaskRecord.task_id == mock_state.task_id).first()
        assert check_rec.status == "success"
        assert check_rec.worker_lock is not None
        print("Test B & F Passed")

        # TEST D & E: Crashed tasks resume correctly & Lock Prevents Double Processing
        print("\n[TEST D & E] Crash Recovery & Lock")
        crash_state = AutonomousTaskState(user_goal="Crashed Goal", status="running")
        crash_rec = repo.save_task_state(crash_state)
        # Manually alter the heartbeat to look like it timed out ages ago
        crash_rec.last_heartbeat = time.time() - 400
        db.commit()
        
        # Attempt claim (simulating crash recovery)
        crash_claim = repo.claim_task_for_worker("recovery_worker")
        assert crash_claim is not None
        assert crash_claim.user_goal == "Crashed Goal"
        
        # The lock was just claimed by recovery_worker... Can another worker claim it?
        concurrent_claim = repo.claim_task_for_worker("bad_worker")
        assert concurrent_claim is None, "Worker took an already locked valid task!"
        print("Test D & E Passed")

        print("\n=== RAW DB RECORD DUMP (Completed Task) ===")
        print(f"Task ID: {check_rec.task_id}")
        print(f"Status: {check_rec.status}")
        print(f"Worker Lock: {check_rec.worker_lock}")
        print(f"Serialized Payload preview: {check_rec.serialized_state[:150]}...")

    print("\n=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    run_verification()
