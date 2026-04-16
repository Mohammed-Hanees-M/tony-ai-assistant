from pydantic import BaseModel, Field
from typing import Any, Optional, Dict
import time

class StreamEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(time.time_ns()))
    event_type: str # token, chunk, meta, done, error, interrupted
    content: Any
    timestamp: float = Field(default_factory=time.time)
    sequence_index: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
