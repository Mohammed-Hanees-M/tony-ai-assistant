import re
from typing import Dict

# Importance Levels
PRIORITY_IMPORTANT = 5  # Explicit memory directives, facts, persistent info
PRIORITY_NORMAL = 3     # Standard conversation
PRIORITY_TRIVIAL = 1    # Greetings, filler, short acknowledgments

# Heuristic Patterns
PATTERNS_IMPORTANT = [
    r"remember (that|this)",
    r"don't forget",
    r"keep in mind",
    r"it is important that",
    r"save this info",
    r"my name is",
    r"i am (a|working|from)",
    r"i (live|work) in",
    r"my (favorite|preferred|preference)",
    r"the (project|business|company) is",
    r"working on",
    r"api key",
    r"url is"
]

PATTERNS_TRIVIAL = [
    r"^(hello|hi|hey|greetings|morning|afternoon|evening)([\s!.,]|$)",
    r"^how are you",
    r"what's up",
    r"^(ok|okay|sure|i see|cool|thanks|thank you|indexed|noted|got it|understood|acknowledged|recorded)([\s!.,]|$)",
    r"^ah([\s!.,]|$)",
    r"^oh([\s!.,]|$)"
]

def score_message_importance(message: Dict[str, str]) -> int:
    """
    Assigns an importance score to a message based on heuristic rules.
    1 = trivial filler
    3 = normal conversation
    5 = important persistent memory
    """
    content = message.get("content", "").lower().strip()
    
    if not content:
        return PRIORITY_TRIVIAL

    # 1. Important Facts / Instructions
    for pattern in PATTERNS_IMPORTANT:
        if re.search(pattern, content):
            return PRIORITY_IMPORTANT
            
    # 2. Trivial / Filler
    for pattern in PATTERNS_TRIVIAL:
        if re.search(pattern, content):
            return PRIORITY_TRIVIAL
            
    # 3. Default Priority
    # Long messages are generally more likely to be important
    if len(content) > 150:
        return PRIORITY_NORMAL + 1 # Slight boost for detailed messages
    
    return PRIORITY_NORMAL
