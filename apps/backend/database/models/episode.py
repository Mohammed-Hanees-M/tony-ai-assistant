from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean
from sqlalchemy.sql import func
from apps.backend.database.base import Base

class EpisodicMemory(Base):
    __tablename__ = "episodic_memories"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), index=True)
    event_type = Column(String(50)) # e.g. task_completion, milestone, decision, debugging, workflow
    summary = Column(Text)
    outcome = Column(Text)
    importance = Column(Integer, default=3)
    tags = Column(String(200), nullable=True) # comma separated
    embedding = Column(Text, nullable=True) # JSON stringified vector
    
    # Governance Metadata
    strength_score = Column(Float, default=1.0)
    access_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)
    reinforcement_count = Column(Integer, default=0)
    decay_exempt = Column(Boolean, default=False)
    archived = Column(Boolean, default=False, index=True)
    
    # Confidence/Trust Metadata
    confidence_score = Column(Float, default=1.0)
    confidence_source = Column(String(50), default="extraction")
    last_confidence_update = Column(DateTime(timezone=True), nullable=True)

    # Provenance / Source Attribution Metadata
    source_type = Column(String(50), nullable=True)
    source_message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)
    source_conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True)
    source_excerpt = Column(Text, nullable=True)
    source_timestamp = Column(DateTime(timezone=True), nullable=True)
    evidence_chain = Column(Text, nullable=True) # Stored JSON list

    created_at = Column(DateTime(timezone=True), server_default=func.now())
