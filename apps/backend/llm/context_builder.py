from typing import Any, List

def build_context(
    user_message: str, 
    history: List[Any] = None, 
    long_term_memories: List[Any] = None,
    summaries: List[Any] = None,
    episodes: List[Any] = None,
    reflections: List[Any] = None
) -> Any:
    """Builds context using all memory tiers: history, summaries, facts, experiences, and learned lessons."""
    if history is None: history = []
    if long_term_memories is None: long_term_memories = []
    if summaries is None: summaries = []
    if episodes is None: episodes = []
    if reflections is None: reflections = []
        
    return {
        "message": user_message,
        "history": [{"role": msg.role, "content": msg.content} for msg in history],
        "long_term_memories": [{"key": m.key, "value": m.value, "confidence": getattr(m, 'confidence_score', 1.0)} for m in long_term_memories],
        "summaries": [s.summary_text for s in summaries],
        "episodes": [
            f"Type: {e.event_type} | Summary: {e.summary} | Outcome: {e.outcome}" 
            for e in episodes
        ],
        "reflections": [r.lesson for r in reflections]
    }
