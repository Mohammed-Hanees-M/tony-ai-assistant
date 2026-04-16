from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import uuid

class KnowledgeEntity(BaseModel):
    entity_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    canonical_name: str
    entity_type: str
    aliases: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class KnowledgeRelation(BaseModel):
    relation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_entity_id: str
    relation_type: str
    target_entity_id: str
    confidence: float = 1.0
    provenance: str = "extracted"
    active: bool = True
