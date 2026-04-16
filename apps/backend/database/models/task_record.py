from sqlalchemy import Column, Integer, String, Text, Boolean, Float
from apps.backend.database.base import Base

class AutonomousTaskRecord(Base):
    __tablename__ = "autonomous_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, unique=True, index=True)
    serialized_state = Column(Text, nullable=False)
    status = Column(String, default="initialized")
    created_at = Column(Float)
    updated_at = Column(Float)
    scheduled_for = Column(Float, nullable=True)
    worker_lock = Column(String, nullable=True)
    last_heartbeat = Column(Float, nullable=True)
