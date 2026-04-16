from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from apps.backend.database.base import Base

class ConversationSummary(Base):
    __tablename__ = "conversation_summaries"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), index=True)
    summary_text = Column(Text)
    covered_message_start_id = Column(Integer)
    covered_message_end_id = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
