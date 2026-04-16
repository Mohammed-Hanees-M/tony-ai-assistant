import time
import uuid
from apps.backend.agent.task_repository import TaskRepository
from apps.backend.agent.autonomous_loop import run_autonomous_task
from sqlalchemy.orm import Session

def run_task_worker_loop(db_session: Session, max_loops: int = 5):
    repo = TaskRepository(db_session)
    worker_id = f"worker_{uuid.uuid4().hex[:8]}"
    
    print(f"\n[WORKER] Starting background worker loop: {worker_id}")
    
    for _ in range(max_loops):
        print(f"[WORKER] Polling for tasks...")
        state = repo.claim_task_for_worker(worker_id)
        
        if not state:
            print("[WORKER] No eligible tasks found. Sleeping...")
            time.sleep(0.5)
            continue
            
        print(f"[WORKER] Processing task for goal: '{state.user_goal}'")
        
        # Resume the existing state inside the autonomous loop
        final_state = run_autonomous_task(state.user_goal, state=state, max_iterations=5)
        
        # Save back the final state to queue
        repo.save_task_state(final_state)
        
        # Heartbeat emulation
        repo.heartbeat(final_state.task_id)
        
    print(f"[WORKER] {worker_id} loop concluded.\n")
