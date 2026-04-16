import os
import sys
from sqlalchemy.orm import Session

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.database.session import SessionLocal
from apps.backend.services.chat_service import process_chat_message
from apps.backend.core.config import CONTEXT_WINDOW_SIZE

def run_audit():
    db = SessionLocal()
    print("=== TONY CONTEXT MEMORY AUDIT ===")
    print(f"Configured CONTEXT_WINDOW_SIZE: {CONTEXT_WINDOW_SIZE}")
    
    # 1. Clean start (new conversation)
    print("\n[Audit-1] Creating new conversation and adding 11 facts...")
    cid = None
    facts = [f"Fact {i} is {i*111}" for i in range(1, 12)] # Fact 1 is 111, ..., Fact 11 is 1221
    
    for fact in facts:
        response, cid = process_chat_message(db, f"Remember this: {fact}", cid)
        # print(f"Tony: {response}")

    print(f"Added 11 facts. Conversation ID: {cid}")

    # 2. Test for forgotten memory (Fact 1)
    # With limit 10: 1 System + 1 Current + 8 History messages.
    # 8 history messages = 4 turns.
    # We added 11 turns. The first 7 turns (Facts 1-7) should be forgotten.
    print(f"\n[Audit-2] Testing if Fact 1 (111) is forgotten...")
    response, cid = process_chat_message(db, "What was Fact 1?", cid)
    print(f"Query: What was Fact 1?")
    print(f"Tony: {response}")
    
    # Verification logic: If it worked, Tony should NOT know what Fact 1 is, 
    # or at least not recall it correctly from context.
    is_forgotten = "111" not in response
    print(f"Result: {'FORGOTTEN' if is_forgotten else 'REMEMBERED (FAIL)'}")

    # 3. Test for recent memory (Fact 11)
    print(f"\n[Audit-3] Testing if Fact 11 is remembered...")
    response, cid = process_chat_message(db, "What was Fact 11?", cid)
    print(f"Query: What was Fact 11?")
    print(f"Tony: {response}")
    
    is_remembered = "Fact 11 is 1221" in response or "1221" in response
    print(f"Result: {'REMEMBERED' if is_remembered else 'FORGOTTEN (FAIL)'}")

    # 4. Final check: History count from logs
    print("\n[Audit-4] Please check the [DEBUG] logs above to verify:")
    print(f"- 'History retrieved' should be {CONTEXT_WINDOW_SIZE - 2}")
    print(f"- 'Sending X messages to Ollama' should be {CONTEXT_WINDOW_SIZE}")

    db.close()

if __name__ == "__main__":
    run_audit()
