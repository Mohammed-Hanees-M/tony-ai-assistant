import random
from typing import Optional
from apps.backend.voice_ux.schemas import VoiceResponseMode

class FollowUpGenerator:
    """Generates contextually useful follow-up prompts for high-value voice interactions."""
    
    FOLLOW_UPS = {
        VoiceResponseMode.FACTUAL: [
            "Was that the information you were looking for?",
            "Should I save this to your memory?",
            "Any other facts I can pull up?"
        ],
        VoiceResponseMode.EDUCATIONAL: [
            "Would you like more details on this topic?",
            "Is that clear, or should I explain it differently?",
            "Do you want me to summarize the main points?"
        ],
        VoiceResponseMode.COMMAND: [
            "What's the next step?",
            "Ready for anything else.",
            "I'm standing by."
        ]
    }

    def generate_followup_prompt(self, mode: VoiceResponseMode) -> Optional[str]:
        # Only 20% follow-up frequency to maintain high UX signal-to-noise
        if random.random() > 0.2:
            return None
            
        options = self.FOLLOW_UPS.get(mode)
        if options:
            return random.choice(options)
        return "Anything else I can help with?"

GLOBAL_FOLLOWUP_GENERATOR = FollowUpGenerator()
