import re

class VoiceToneOptimizer:
    """Optimizes text for spoken cadence and conversational naturalness."""
    
    CONTRACTIONS = {
        r"\bit is\b": "it's",
        r"\bIt is\b": "It's",
        r"\bthat is\b": "that's",
        r"\bThat is\b": "That's",
        r"\bI am\b": "I'm",
        r"\bdo not\b": "don't",
        r"\bDo not\b": "Don't",
        r"\bcannot\b": "can't",
        r"\bCannot\b": "Can't"
    }

    def optimize_for_spoken_conversation(self, text: str) -> str:
        # 1. Apply contractions (deterministic casing)
        for pattern, replacement in self.CONTRACTIONS.items():
            text = re.sub(pattern, replacement, text)
            
        # 2. Remove robotic preambles
        preambles = [
            r"^(As an AI (assistant|language model),?\s*)",
            r"^(I can confirm that,?\s*)",
            r"^(According to my analysis,?\s*)",
            r"^(I have processed your request, and\s*)"
        ]
        for p in preambles:
            text = re.sub(p, "", text, flags=re.I)
            
        # 3. Capitalize correctly
        text = text[0].upper() + text[1:] if text else ""
        
        return text.strip()

GLOBAL_TONE_OPTIMIZER = VoiceToneOptimizer()
