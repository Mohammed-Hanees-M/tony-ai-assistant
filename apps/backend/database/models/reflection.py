from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey
from sqlalchemy.sql import func
from apps.backend.database.base import Base

class ReflectiveMemory(Base):
    __tablename__ = "reflective_memories"

    id = Column(Integer, primary_key=True, index=True)
    lesson = Column(Text)
    context = Column(String(100), index=True) # e.g. coding, user_preference, architecture
    confidence_score = Column(Float, default=0.5)
    confidence_source = Column(String(50), default="reflection")
    last_confidence_update = Column(DateTime(timezone=True), nullable=True)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    importance = Column(Integer, default=3)
    embedding = Column(Text, nullable=True) # JSON stringified vector
    
    # Governance Metadata
    strength_score = Column(Float, default=1.0)
    access_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)
    reinforcement_count = Column(Integer, default=0)
    decay_exempt = Column(Boolean, default=False)
    archived = Column(Boolean, default=False, index=True)

    # Provenance / Source Attribution Metadata
    source_type = Column(String(50), nullable=True)
    source_message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)
    source_conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True)
    source_excerpt = Column(Text, nullable=True)
    source_timestamp = Column(DateTime(timezone=True), nullable=True)
    evidence_chain = Column(Text, nullable=True) # Stored JSON list

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
