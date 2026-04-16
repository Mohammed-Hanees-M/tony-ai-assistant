from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean
from sqlalchemy.sql import func
from apps.backend.database.base import Base

class LongTermMemory(Base):
    __tablename__ = "long_term_memories"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), index=True)
    value = Column(Text)
    category = Column(String(50), index=True) # e.g. identity, preference, project, etc.
    importance = Column(Integer, default=1)
    source_message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)
    embedding = Column(Text, nullable=True) # Stores JSON stringified vector
    
    # Governance Metadata
    strength_score = Column(Float, default=1.0)
    access_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)
    reinforcement_count = Column(Integer, default=0)
    decay_exempt = Column(Boolean, default=False)
    archived = Column(Boolean, default=False, index=True)
    
    # Conflict/Supersession Metadata
    superseded = Column(Boolean, default=False, index=True)
    superseded_by = Column(Integer, nullable=True) # ID of the replacing memory
    supersedes = Column(Integer, nullable=True)     # ID of the memory this replaced
    corrected_at = Column(DateTime(timezone=True), nullable=True)
    
    # Confidence/Trust Metadata
    confidence_score = Column(Float, default=1.0)
    confidence_source = Column(String(50), default="explicit")
    last_confidence_update = Column(DateTime(timezone=True), nullable=True)

    # Provenance / Source Attribution Metadata
    source_type = Column(String(50), nullable=True)
    source_conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True)
    source_excerpt = Column(Text, nullable=True)
    source_timestamp = Column(DateTime(timezone=True), nullable=True)
    evidence_chain = Column(Text, nullable=True) # Stored JSON list

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
