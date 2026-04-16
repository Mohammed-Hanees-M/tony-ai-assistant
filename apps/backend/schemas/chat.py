from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class ChatMessageRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None


class ChatMessageResponse(BaseModel):
    response: str
    conversation_id: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)