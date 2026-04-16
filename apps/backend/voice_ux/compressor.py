import re
from apps.backend.voice_ux.schemas import VoiceResponseMode

class VoiceCompressor:
    """Semantic sentence-aware compression for voice delivery."""
    
    def compress_to_voice_friendly(self, text: str, mode: VoiceResponseMode) -> str:
        if not text:
            return ""

        # Deterministic limits based on mode
        max_words = 35 if mode == VoiceResponseMode.EMOTIONAL else 25
        max_sentences = 2
        
        # 1. Split into sentences intelligently
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        
        # 2. Heuristic: Keep the first one and potentially the second if it's not too long
        result_sentences = []
        word_count = 0
        
        for idx, s in enumerate(sentences):
            if idx >= max_sentences:
                break
            
            s_words = s.split()
            if word_count + len(s_words) > max_words:
                # If the first sentence is already over the limit, we must keep it but maybe trim filler
                if idx == 0:
                    # Truncate words but wrap at sentence level
                    result_sentences.append(" ".join(s_words[:max_words]).strip(".") + "...")
                break
            
            result_sentences.append(s)
            word_count += len(s_words)

        return " ".join(result_sentences)

GLOBAL_COMPRESSOR = VoiceCompressor()
