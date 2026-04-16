import re
from typing import Tuple, Optional
from apps.backend.conversation.context_manager import get_session_context, DialogueState
from apps.backend.conversation.dialogue_act import classify_dialogue_act
from apps.backend.llm.inference import run_llm_inference

RESOLVER_PROMPT = """
Transform the conversational follow-up into a standalone query.
Output ONLY the concise, natural language query. No preambles.

Context:
Last User Query: {last_query}
Active Topic: {active_topic}
"""

AMBIGUITY_PROMPT = """Analyze for ambiguity. If unclear, return 'AMBIGUOUS: <QUESTION>'. Else 'CLEAR'."""

# Deterministic Follow-Up Templates
FOLLOW_UP_TEMPLATES = {
    r"summarize\s+(it|that|this)": "Summarize {topic}",
    r"explain\s+(it|that|this|more)": "Explain {topic} in more detail",
    r"explain\s+in\s+detail": "Explain {topic} in more detail",
    r"simplify\s+(it|that|this)": "Explain {topic} more simply",
    r"explain\s+(it|that|this)\s+more\s+simply": "Explain {topic} more simply",
    r"(can\s+you\s+)?give\s+(me\s+)?an\s+example": "Provide a practical real-world example of {topic}",
    r"example\??": "Provide a practical real-world example of {topic}",
    r"show\s+(me\s+)?an\s+example": "Provide a practical real-world example of {topic}",
    r"another\s+one\s+like\s+this": "Provide another practical example of {topic}",
    r"tell\s+me\s+more": "Tell me more about {topic}",
    r"elaborate": "Elaborate on {topic}",
    r"why\??": "Why {topic}?",
    r"how\??": "How {topic}?",
    r"why\s+is\s+it\s+important\??": "Why is {topic} important?",
    r"is\s+it\s+important\??": "Is {topic} important?",
    r"how\s+does\s+it\s+work\??": "How does {topic} work?",
    r"compare\s+them": "Compare {topic} with previous entities",
    r"compare\s+that": "Compare {topic} with similar concepts",
    r"continue": "Continue the explanation about {topic}",
    r"go\s+deeper": "Provide a more advanced in-depth analysis of {topic}",
    r"what\s+do\s+you\s+mean": "Clarify the previous statement about {topic} in more detail",
    r".*example\s+for\s+that": "Provide an example of {topic}",
    r".*example\s+of\s+that": "Provide an example of {topic}",
    r".*practical\s+example": "Provide a practical example of {topic}",
    r".*daily\s+use\s+example": "Provide a daily use example of {topic}",
    r".*real\s+world\s+example": "Provide a real world example of {topic}",
    r".*use\s+cases": "What are the common use cases for {topic}?",
    r".*applications": "What are the practical applications of {topic}?",
    r".*where\s+is\s+it\s+used": "Where is {topic} used in the real world?",
    r".*benefits": "What are the benefits of {topic}?",
    r".*drawbacks": "What are the drawbacks and limitations of {topic}?",
    r".*advantages": "What are the advantages of using {topic}?",
    r".*disadvantages": "What are the disadvantages of {topic}?",
    r"(yes,?\s+)?give\s+(me\s+)?more\s+detail": "Explain {topic} in more detail",
    r"(yes,?\s+)?tell\s+me\s+more": "Tell me more about {topic}"
}

def resolve_contextual_query(query: str, session_id: str, model: str = "phi3") -> Tuple[str, bool, Optional[str]]:
    """
    Dialogue-Act Driven Query Resolution.
    Enforces deterministic resolution for 100% of standard follow-up triggers.
    """
    # Normalize Query: Collapse duplicates (e.g., "it! it!" -> "it")
    q_norm = re.sub(r'(\b\w+\b)(?:[!\?\s,]+\1\b)+', r'\1', query, flags=re.IGNORECASE)
    
    state = get_session_context(session_id)
    act = classify_dialogue_act(q_norm)
    q_low = q_norm.lower().strip()
    topic = state.primary_topic or "the previous topic"

    
    print(f"[CONTEXT] Dialogue Act Detected: {act}")

    # --- 1. ACKNOWLEDGEMENT / AFFIRMATION: Contextual Continuation ---
    if act in ["ACKNOWLEDGEMENT", "AFFIRMATION"]:
        # Check if affirmation contains a follow-up phrase (e.g., "Yes, give me more detail")
        q_match = q_low.rstrip(' .?!')
        for pattern, template in FOLLOW_UP_TEMPLATES.items():
            if re.search(pattern, q_match):
                resolved = template.format(topic=topic)
                print(f"[CONTEXT] Combined Affirmation/Follow-Up Resolved: '{query}' -> '{resolved}'")
                return resolved, False, None

        if act == "AFFIRMATION" and state.primary_topic:
             print(f"[CONTEXT] Affirmation Resolved: '{query}' -> 'Tell me more about {topic}'")
             return f"Tell me more about {topic}", False, None
        return q_norm, False, None

    # --- 1.1 CORRECTION: Contextual Re-evaluation ---
    if act == "CORRECTION":
        print(f"[CONTEXT] User Correction Detected. Forcing re-evaluation of '{topic}'")
        return f"Correct your previous answer about {topic}", False, None

    # --- 2. AMBIGUOUS FRAGMENT: Clarify ---
    if act == "AMBIGUOUS_FRAGMENT":
        print(f"[CONTEXT] Ambiguity Detected: '{query}'")
        clarification = f"Could you clarify what you mean by '{query}'? I want to make sure I help you correctly."
        return query, True, clarification

    # --- 3. FOLLOW_UP: STRICT DETERMINISTIC RESOLUTION ---
    if act == "FOLLOW_UP":
        # Normalize for matching: strip trailing punctuation and dots
        q_match = q_low.rstrip(' .?!')
        
        # 3.1 PLURAL REFERENCE RESOLUTION (both, them, those, the two)
        plural_keywords = ["both", "them", "those", "the two", "summarize both", "summarize them", "compare them", "examples for both"]
        if any(kw in q_match for kw in plural_keywords) and len(state.active_topics) >= 2:
            topics_str = " and ".join(state.active_topics[:2])
            if "compare" in q_match:
                resolved = f"Compare {topics_str}"
            elif "summarize" in q_match or "both" == q_match or "them" == q_match:
                resolved = f"Summarize both {topics_str}"
            elif "example" in q_match:
                resolved = f"Provide a practical example for both {state.active_topics[0]} and {state.active_topics[1]}"
            else:
                resolved = f"{query} regarding {topics_str}"
            
            print(f"[CONTEXT] Plural Reference Resolved: '{query}' -> '{resolved}'")
            return resolved, False, None

        # 3.2 Standard Single Topic Resolution
        topic = state.primary_topic or "the previous topic"
        
        # Check deterministic templates (0ms overhead)
        for pattern, template in FOLLOW_UP_TEMPLATES.items():
            if re.fullmatch(pattern, q_match) or q_match == pattern:
                resolved = template.format(topic=topic)
                print(f"[CONTEXT] Deterministic Follow-Up Template Applied: '{query}' -> '{resolved}'")
                return resolved, False, None
        
        # Hard Fallback for unmapped follow-ups: Subject-Pasting (NO LLM REWRITE)
        if len(q_low.split()) <= 3:
            resolved = f"{query} regarding {topic}"
            print(f"[CONTEXT] Heuristic Follow-Up Resolve: '{query}' -> '{resolved}'")
            return resolved, False, None

        # Deep Fallback: Only for truly complex, non-standard ambiguous expansions
        print(f"[CONTEXT] Resolving complex amorphous follow-up via LLM (Model: {model})...")
        messages = [
            {"role": "system", "content": RESOLVER_PROMPT.format(
                last_query=state.last_query_trimmed(),
                active_topic=topic
            )},
            {"role": "user", "content": query}
        ]
        resolved = run_llm_inference(messages, model).strip().strip('"')
        
        # Strict Integrity Check
        if len(resolved.split()) > len(query.split()) + 5 or topic.lower() not in resolved.lower():
             print(f"[CONTEXT][WARN] Hallucination detected. Forcing topic grounding.")
             resolved = f"{query} regarding {topic}"
             
        return resolved, False, None

        
    return query, False, None
        
    return query, False, None

def sanitize_response(text: str) -> str:
    """Hard firewall blocking internal architectural terminology."""
    blocklist = [
        r"===.*?===", 
        r"MATRIX KNOWLEDGE GRAPH", r"SEMANTIC MEMORY", r"EPISODIC MEMORY",
        r"RETRIEVAL ENGINE", r"INTERNAL CONTEXT", r"SYSTEM PROMPT",
        r"TOOL TRACE", r"JSON TRACE", r"COGNITIVE PIPELINE", r"GRAPH MATRIX",
        r"RELEVANT INFORMATION", r"FUSE_WITH_MEMORY",
        r"KNOWLEDGE MATRIX", r"SEMANTIC MATRIX", r"GRAPH KNOWLEDGE", r"UNDERSTANDING MATRIX",
        r"RECURRENT MODEL", r"EPISODIC CONTENT", r"SIMULATION MATRIX", r"TRACE LOGS",
        r"SEMANTIC", r"GRAPH", r"MATRIX", r"RETRIEVAL", r"CONTEXT", r"INTERNAL TRACE", r"KNOWLEDGE BASE",
        r"OPENAI", r"MICROSOFT", r"GPT-3", r"GPT-4", r"TRAINING DATA CUTOFF", r"KNOWLEDGE CUTOFF", r"LANGUAGE MODEL"
    ]
    sanitized = text
    for pattern in blocklist:
        sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE | re.DOTALL)
    
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    return sanitized
