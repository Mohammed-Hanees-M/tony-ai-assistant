from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
import time

class ConversationSession(BaseModel):
    session_id: str
    user_id: str
    active_conversation_id: Optional[str] = None
    active_stream_id: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    last_active_at: float = Field(default_factory=time.time)
    status: str = "active" # active, idle, closed
    metadata: Dict[str, Any] = Field(default_factory=dict)
