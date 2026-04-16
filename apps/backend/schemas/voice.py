from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import time

class VoiceTranscript(BaseModel):
    text: str
    confidence: float
    language: str = "en"
    duration_ms: float = 0.0
    model_used: str = "whisper-tiny"
    timestamp: float = Field(default_factory=time.time)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    is_clarification_required: bool = False

class VoiceState(BaseModel):
    session_id: str
    status: str = "idle" # idle, listening, thinking, speaking, interrupted
    last_state_change: float = Field(default_factory=time.time)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AudioChunk(BaseModel):
    data: bytes
    sequence_index: int
    duration_ms: float = 0.0
    is_final: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)
