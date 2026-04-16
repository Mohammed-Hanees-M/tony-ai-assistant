from pydantic import BaseModel, Field
from typing import Optional
import uuid

class WorkflowStrategyProfile(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_pattern: str
    context_pattern: str
    success_rate: float = 0.0
    avg_latency_ms: float = 0.0
    usage_count: int = 0
    confidence: float = 0.0
    preferred: bool = False
    notes: str = ""
