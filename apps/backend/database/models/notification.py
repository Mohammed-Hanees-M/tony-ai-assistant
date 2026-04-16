from sqlalchemy import Column, Integer, String, Text, Float, Boolean
from apps.backend.database.base import Base

class NotificationEvent(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, unique=True, index=True)
    user_id = Column(String, nullable=True)
    event_type = Column(String, index=True)
    title = Column(String)
    message = Column(Text)
    payload_json = Column(Text)
    related_task_id = Column(String, nullable=True, index=True)
    created_at = Column(Float)
    read_at = Column(Float, nullable=True)
    acknowledged = Column(Boolean, default=False)
