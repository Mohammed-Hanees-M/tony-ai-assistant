import json
import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class DialogueState(BaseModel):
    session_id: str
    active_topics: List[str] = Field(default_factory=lambda: ["general conversation"])
    primary_topic: Optional[str] = "general conversation"
    active_entities: List[str] = Field(default_factory=list)
    last_user_query: Optional[str] = None
    last_tony_response: Optional[str] = None
    last_dialogue_act: str = "CHITCHAT"
    awaiting_clarification: bool = False
    turn_count: int = 0
    last_tool_action: Optional[str] = None
    last_explanation_subject: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)


    def last_query_trimmed(self, max_words: int = 15) -> str:
        if not self.last_user_query: return ""
        words = self.last_user_query.split()
        if len(words) <= max_words: return self.last_user_query
        return " ".join(words[:max_words]) + "..."

# In-memory storage for session context (In production, this would be Redis/DB)
_SESSION_CONTEXT_STORE: Dict[str, DialogueState] = {}

def get_session_context(session_id: str) -> DialogueState:
    if session_id not in _SESSION_CONTEXT_STORE:
        _SESSION_CONTEXT_STORE[session_id] = DialogueState(session_id=session_id)
    return _SESSION_CONTEXT_STORE[session_id]

def update_session_context(session_id: str, updates: Dict[str, Any]):
    context = get_session_context(session_id)
    for k, v in updates.items():
        if hasattr(context, k):
            setattr(context, k, v)
    context.timestamp = time.time()
    context.turn_count += 1

def clear_session_context(session_id: str):
    if session_id in _SESSION_CONTEXT_STORE:
        del _SESSION_CONTEXT_STORE[session_id]
