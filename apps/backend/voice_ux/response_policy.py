import re
from typing import Any, Dict
from apps.backend.voice_ux.schemas import VoiceResponseMode

class ResponsePolicyRouter:
    """Classifies user intent and response context to determine the optimal voice delivery mode."""
    
    def classify_response_mode(self, user_query: str, assistant_output: str, cognitive_trace: Any) -> VoiceResponseMode:
        query = user_query.lower()
        output = assistant_output.lower()
        
        # 1. COMMAND detection
        command_keywords = ["open", "start", "stop", "play", "set", "turn", "call", "send"]
        if any(query.startswith(k) for k in command_keywords) or len(output.split()) < 5:
            return VoiceResponseMode.COMMAND
            
        # 2. CLARIFICATION detection
        if "?" in output and ("sorry" in output or "did you mean" in output or "repeat" in output):
            return VoiceResponseMode.CLARIFICATION
            
        # 3. FACTUAL detection
        if any(k in query for k in ["who", "where", "when", "how much", "what time", "what is the capital", "what is the height"]):
            return VoiceResponseMode.FACTUAL

        # 4. EDUCATIONAL detection
        edu_keywords = ["how", "why", "explain", "what is", "teach", "describe"]
        if any(k in query for k in edu_keywords) or len(output) > 200:
            return VoiceResponseMode.EDUCATIONAL

        # 5. EMOTIONAL detection
        emo_keywords = ["sad", "happy", "bad", "angry", "scared", "love", "feel"]
        if any(k in query for k in emo_keywords) or any(k in output for k in ["sorry to hear", "congratulations", "glad"]):
            return VoiceResponseMode.EMOTIONAL
            
        # 6. Default CASUAL
        return VoiceResponseMode.CASUAL

GLOBAL_POLICY_ROUTER = ResponsePolicyRouter()
