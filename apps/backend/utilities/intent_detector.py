import re
from typing import Optional

TEMPORAL_PATTERNS = [
    r"what(\s+is|\'s)?\s+(the\s+)?(current\s+)?(date|time|day|year|month)",
    r"(tell|give)(\s+me)?\s+(the\s+)?(date|time|day|year|month)",
    r"what's\s+today's\s+date",
    r"what\s+day\s+is\s+it",
    r"time\s+is\s+it",
    r"current\s+date\s+and\s+time",
]

IDENTITY_PATTERNS = [
    r"who\s+(created|designed|built|made)\s+you",
    r"who\s+is\s+your\s+(creator|owner|designer|builder)",
    r"who\s+own(s)?\s+you",
    r"what(\s+is|\'s)\s+your\s+name",
    r"who\s+are\s+you",
    r"tell\s+me\s+about\s+yourself",
]

def detect_utility_intent(query: str) -> Optional[str]:
    """
    Detects deterministic utility intents in conversational text.
    Returns the utility name (e.g., 'system_clock') or None.
    """
    q = query.lower().strip()
    
    # 1. Identity / Persona
    for pattern in IDENTITY_PATTERNS:
        if re.search(pattern, q):
            return "identity_profile"

    # 2. Temporal / System Clock
    for pattern in TEMPORAL_PATTERNS:
        if re.search(pattern, q):
            return "system_clock"
            
    # Specialized keywords (fallback for very short queries)
    if q in ["time", "date", "today", "clock"]:
        return "system_clock"
        
    return None

def detect_web_requirement(query: str) -> bool:
    """
    Detects if a query requires fresh information from the web.
    """
    q = query.lower().strip()
    web_keywords = [
        "search", "browse", "find", "latest", "news", "current", "weather", 
        "today", "online", "who is", "what is", "price", "stock"
    ]
    # Specific check for fresh knowledge indicators
    if any(kw in q for kw in ["latest", "news", "today's", "current"]):
        return True
        
    # Check for search-like commands
    if q.startswith(("search", "find", "look up", "google")):
        return True
        
    return False
