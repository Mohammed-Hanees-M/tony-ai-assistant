import re
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from apps.backend.database.models.memory import LongTermMemory

def detect_explicit_correction(text: str) -> bool:
    """Detects if the user message contains phrasing indicative of a correction."""
    correction_patterns = [
        r"\bactually\b",
        r"\bcorrection\b",
        r"\bupdate\b",
        r"\bchanged my mind\b",
        r"\bno, I meant\b",
        r"\binstead of\b",
        r"\bit's not .* anymore\b",
        r"\bnot anymore\b"
    ]
    lowered = text.lower()
    return any(re.search(pattern, lowered) for pattern in correction_patterns)

def handle_memory_supersession(db: Session, old_memory: LongTermMemory, new_memory: LongTermMemory):
    """
    Links two memories in a supersession chain.
    The old memory is archived and marked as superseded.
    """
    print(f"[CONFLICT] Superseding Memory ID {old_memory.id} ('{old_memory.value}')")
    print(f"[CONFLICT] New Value: '{new_memory.value}'")
    
    old_memory.superseded = True
    old_memory.superseded_by = new_memory.id
    old_memory.archived = True # Conflicts also trigger archival to keep context clean
    
    new_memory.supersedes = old_memory.id
    new_memory.corrected_at = datetime.now(timezone.utc)
    
    db.commit()
    print(f"[CONFLICT] Resolution: ID {new_memory.id} now supersedes ID {old_memory.id}")
