import time
import json
from typing import List, Optional
from apps.backend.schemas.agent import AutonomousTaskState
from apps.backend.database.models.task_record import AutonomousTaskRecord
from sqlalchemy.orm import Session
from sqlalchemy import or_

class TaskRepository:
    def __init__(self, db_session: Session):
        self.db = db_session
        
    def save_task_state(self, state: AutonomousTaskState, scheduled_for: float = None):
        record = self.db.query(AutonomousTaskRecord).filter(
            AutonomousTaskRecord.task_id == state.task_id
        ).first()
        
        now = time.time()
        ser_state = state.model_dump_json()
        
        if record:
            record.serialized_state = ser_state
            record.status = state.status
            record.updated_at = now
            if scheduled_for is not None:
                record.scheduled_for = scheduled_for
        else:
            record = AutonomousTaskRecord(
                task_id=state.task_id,
                serialized_state=ser_state,
                status=state.status,
                created_at=now,
                updated_at=now,
                scheduled_for=scheduled_for
            )
            self.db.add(record)
            
        self.db.commit()
        print(f"[TASK REC] Task {state.task_id} saved to DB. Status: {state.status}")
        return record
        
    def claim_task_for_worker(self, worker_id: str, timeout_sec: int = 300) -> Optional[AutonomousTaskState]:
        now = time.time()
        
        # Standard query to find pending OR crashed tasks
        task = self.db.query(AutonomousTaskRecord).filter(
            or_(
                AutonomousTaskRecord.status == "initialized",
                AutonomousTaskRecord.status == "pending",
                (AutonomousTaskRecord.status == "running") & (AutonomousTaskRecord.last_heartbeat < now - timeout_sec)
            )
        ).filter(
            or_(
                AutonomousTaskRecord.scheduled_for == None,
                AutonomousTaskRecord.scheduled_for <= now
            )
        ).first()
        
        if not task:
            return None
            
        if task.status == "running":
            print(f"[TASK REC] Crash recovery activated for task: {task.task_id}")
            
        # Lock
        task.worker_lock = worker_id
        task.last_heartbeat = now
        task.status = "running"
        self.db.commit()
        
        print(f"[TASK REC] Worker {worker_id} claimed task {task.task_id} successfully.")
        
        state_dict = json.loads(task.serialized_state)
        state_dict["status"] = "running"
        return AutonomousTaskState(**state_dict)
        
    def heartbeat(self, task_id: str):
        task = self.db.query(AutonomousTaskRecord).filter(AutonomousTaskRecord.task_id == task_id).first()
        if task:
            task.last_heartbeat = time.time()
            self.db.commit()
