import random
import re
from typing import Optional

SOCIAL_MAP = {
    r"\b(hello|hi|hey|greetings|howdy)\b": [
        "Hello! How can I help you today?",
        "Hi there! What's on your mind?",
        "Greetings! How can I assist you?",
        "Hey! Ready to dive into something?"
    ],
    r"\b(good\s+morning)\b": [
        "Good morning! Hope your day is off to a great start.",
        "Morning! How can I help you today?"
    ],
    r"\b(good\s+afternoon)\b": [
        "Good afternoon! How is your day going?",
        "Good afternoon! What's the plan for today?"
    ],
    r"\b(good\s+evening)\b": [
        "Good evening! How can I assist you tonight?",
        "Evening! Hope you're having a productive night."
    ],
    r"\b(thank\s+you|thanks|much\s+obliged)\b": [
        "You're very welcome!",
        "Happy to help!",
        "No problem at all!",
        "Anytime!"
    ],
    r"\b(bye|goodbye|see\s+you|talk\s+later)\b": [
        "Goodbye! Have a great day.",
        "Talk to you later!",
        "See you soon!",
        "Take care!"
    ],
    r"\b(how\s+are\s+you|how\s+is\s+it\s+going)\b": [
        "I'm doing great, thank you for asking! How are you?",
        "Everything is running smoothly! How about yourself?",
        "I'm powered up and ready to go! How are things with you?"
    ],
    r"\b(who\s+are\s+you|what\s+is\s+your\s+name)\b": [
        "I am Tony, your AI assistant, built and owned by Mohammed Hanees Mullakkal."
    ]
}

def resolve_social_query(query: str) -> Optional[str]:
    """Deterministic social router for ultra-low latency response."""
    q = query.lower().strip().strip('?!.')
    for pattern, responses in SOCIAL_MAP.items():
        if re.search(pattern, q):
            return random.choice(responses)
    return None
