from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import re
from apps.backend.database.models.settings import Settings
from apps.backend.core.constants import MODEL_TIER_1, MODEL_TIER_2, SETTING_MODEL_SELECTION

def route_model(query: str, purpose: str = "chat", complexity: float = 0.0, act: str = "QUESTION") -> str:
    """
    Tiered Model Router:
    - Tier 1 (phi3): Casual, social, greetings, acknowledgements, low-complexity.
    - Tier 2 (llama3): Factual, technical, scientific, reasoning, summarization, multi-turn.
    """
    q_low = query.lower().strip()
    
    # Identify Technical/Scientific Keywords
    technical_triggers = [
        r"\bquantum\b", r"\brelativity\b", r"\bphysics\b", r"\bmechanics\b",
        r"\bmachine learning\b", r"\bai\b", r"\bneural\b", r"\bnetwork\b",
        r"\bcode\b", r"\bprogram\b", r"\bpython\b", r"\balgorithm\b",
        r"\bexplain\b", r"\bhow does\b", r"\bwhy\b", r"\bcompare\b"
    ]
    
    is_technical = any(re.search(pattern, q_low) for pattern in technical_triggers)
    
    # --- ROUTING LOGIC ---
    
    # 1. Tier 2 (Llama3) for high-value tasks
    if purpose in ["summarization", "reasoning", "verification", "refinement", "extraction"]:
        reason = f"High-precision {purpose} task"
        print(f"[MODEL ROUTER] Selected: {MODEL_TIER_2} (Reason: {reason})")
        return MODEL_TIER_2

    if is_technical or complexity > 0.3 or act == "FOLLOW_UP":
        reason = "technical_query" if is_technical else "complex_logic"
        if act == "FOLLOW_UP": reason = "contextual_follow_up"
        print(f"[MODEL ROUTER] Selected: {MODEL_TIER_2} (Reason: {reason})")
        return MODEL_TIER_2

    # 2. Tier 1 (Phi3) for casual/social tasks
    if act in ["CHITCHAT", "ACKNOWLEDGEMENT", "AFFIRMATION"] and not is_technical:
        reason = "casual_interaction"
        print(f"[MODEL ROUTER] Selected: {MODEL_TIER_1} (Reason: {reason})")
        return MODEL_TIER_1

    # Default to Tier 2 for safety/quality
    print(f"[MODEL ROUTER] Selected: {MODEL_TIER_2} (Reason: default_high_quality)")
    return MODEL_TIER_2

def select_model(user_message: str, db: Optional[Session] = None, purpose: str = "chat", complexity: float = 0.0, act: str = "QUESTION") -> str:
    """Entry point for model selection. Checks DB overrides then routes via tiered logic."""
    
    # 1. Check for manual override in DB
    if db:
        try:
            setting = db.query(Settings).filter(Settings.key == SETTING_MODEL_SELECTION).first()
            if setting and setting.value:
                # If a specific model like 'gemini' is selected, return it immediately
                return setting.value
        except Exception:
            pass
            
    # 2. Dynamic Routing
    return route_model(user_message, purpose, complexity, act)
