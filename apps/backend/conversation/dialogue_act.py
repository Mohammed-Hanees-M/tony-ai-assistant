import re
from typing import List

# Act Keywords & Patterns
ACT_KEYWORDS = {
    "ACKNOWLEDGEMENT": [r"that's\s+interesting", r"i\s+see", r"ok", r"cool", r"nice", r"understand", r"got\s+it", r"correct", r"right", r"thanks", r"thank\s+you"],
    "FOLLOW_UP": [
        r"summarize\s+(it|that|this)", 
        r"explain\s+(it|that|this|more)", 
        r"explain\s+in\s+detail",
        r"simplify\s+(it|that|this|that|more)",
        r"(can\s+you\s+)?give\s+(me\s+)?an\s+example",
        r"example\??",
        r"show\s+(me\s+)?an\s+example",
        r"tell\s+me\s+more", 
        r"elaborate", 
        r"compare\s+them", 
        r"compare\s+that",
        r"continue",
        r"go\s+deeper",
        r"what\s+do\s+you\s+mean",
        r"why\s+is\s+it\s+important",
        r"is\s+it\s+important",
        r"how\s+does\s+it\s+work",
        r"example\s+for\s+that",
        r"example\s+of\s+that",
        r"practical\s+example",
        r"daily\s+use\s+example",
        r"real\s+world\s+example",
        r"use\s+cases",
        r"applications",
        r"where\s+is\s+it\s+used",
        r"benefits",
        r"drawbacks",
        r"advantages",
        r"disadvantages",
        r"give\s+(me\s+)?more\s+detail",
        r"tell\s+me\s+everything",
        r"tell\s+me\s+more\s+about\s+(it|this)",
        r"(describe|detail)\s+(it|this)"
    ],
    "AFFIRMATION": [r"^yes\b", r"go\s+ahead", r"proceed", r"continue", r"next", r"sounds\s+good", r"that's\s+fine"],
    "CORRECTION": [r"that's\s+wrong", r"incorrect", r"not\s+right", r"you\s+made\s+a\s+mistake", r"wrong\s+answer", r"no\s+it's\s+not", r"wrong\s+buddy", r"wrong\s+person", r"not\s+the\s+right\s+answer", r"check\s+again"],
    "AMBIGUOUS_FRAGMENT": [r"about\s+[a-z]+$", r"and\s+[a-z]+$", r"raise\s+it$", r"the\s+other\s+one$"],
    "CHITCHAT": [r"hello", r"hi", r"how\s+are\s+you", r"who\s+are\s+you"]
}

def classify_dialogue_act(query: str) -> str:
    """Deterministic classification of the dialogue act per turn."""
    q = query.lower().strip()
    
    # Check for direct follow-up phrases (Phase 1)
    for act, patterns in ACT_KEYWORDS.items():
        for pattern in patterns:
            if re.search(pattern, q):
                  # Hard Restraint for Affirmations: Must be short
                  if act == "AFFIRMATION" and len(q.split()) > 3:
                      continue
                  return act
                  
    # Check for fragments
    if len(q.split()) <= 2:
        if any(w in q for w in ["it", "that", "this", "them", "those", "why", "how"]):
            return "FOLLOW_UP"
        if q not in ["hello", "hi", "thanks", "ok"]:
            return "AMBIGUOUS_FRAGMENT"

    # Default acts
    if "?" in q or any(q.startswith(w) for w in ["what", "who", "where", "when", "why", "how", "can", "could", "which"]):
        return "QUESTION"
        
    return "COMMAND" if any(q.startswith(w) for w in ["run", "open", "search", "show", "get"]) else "CHITCHAT"
