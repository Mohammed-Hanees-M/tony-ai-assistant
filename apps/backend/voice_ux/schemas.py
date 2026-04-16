from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional

class VoiceResponseMode(str, Enum):
    FACTUAL = "factual"
    COMMAND = "command"
    EDUCATIONAL = "educational"
    EMOTIONAL = "emotional"
    CASUAL = "casual"
    CLARIFICATION = "clarification"

class VoiceUXConfig(BaseModel):
    max_words: int = 25
    max_sentences: int = 2
    latency_threshold_ms: int = 500
    filler_cooldown_seconds: int = 10

class VoiceUXState(BaseModel):
    last_filler_time: float = 0.0
    current_mode: VoiceResponseMode = VoiceResponseMode.CASUAL

class OptimizedVoiceResponse(BaseModel):
    original_text: str
    optimized_text: str
    mode: VoiceResponseMode
    follow_up: Optional[str] = None
    was_compressed: bool = False
