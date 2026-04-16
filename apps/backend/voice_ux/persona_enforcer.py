import re

class PersonaEnforcer:
    """Enforces Tony's premium, confident and polished persona in post-processing."""
    
    WEAK_PHRASES = [
        (r"I think (that )?", "It looks like "),
        (r"Maybe (we could|you should)", "I recommend "),
        (r"I'm not entirely sure, but", "Based on what I see,"),
        (r"Actually, ", ""), # "Actually" can sound condescending or defensive
        (r"Just ", ""), # Removes minimize-words
    ]

    def enforce_tony_persona(self, text: str) -> str:
        # 1. Substitute weak phrasing with confident alternatives
        for weak, strong in self.WEAK_PHRASES:
            text = re.sub(weak, strong, text, flags=re.I)
            
        # 2. Ensure "Tony" signature style (confident, helpful, slightly sophisticated)
        # Tony doesn't say "No problem", he says "My pleasure" or "Of course"
        text = re.sub(r"No problem", "Of course", text, flags=re.I)
        
        return text.strip()

GLOBAL_PERSONA_ENFORCER = PersonaEnforcer()
