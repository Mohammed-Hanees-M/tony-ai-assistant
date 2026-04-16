import random
import time
from typing import Optional
from apps.backend.voice_ux.schemas import VoiceUXState

class LatencyMasker:
    """Emits latent-fillers if processing time exceeds threshold, with cooldown logic."""
    
    FILLERS = [
        "One moment, let me check that.",
        "Just a second, looking into it.",
        "Let me see...",
        "I'm on it. Just a moment.",
        "Right, let me pull that up."
    ]

    def __init__(self):
        self.state = VoiceUXState()

    def maybe_emit_latency_mask(self, elapsed_ms: float) -> Optional[str]:
        # 1. Condition: elapsed > 500ms
        if elapsed_ms < 500:
            return None
            
        # 2. Condition: Cooldown (10s)
        current_time = time.time()
        if (current_time - self.state.last_filler_time) < 10:
            return None
            
        # 3. Emit and update state
        self.state.last_filler_time = current_time
        return random.choice(self.FILLERS)

GLOBAL_LATENCY_MASKER = LatencyMasker()
