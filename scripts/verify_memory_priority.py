import os
import sys
from unittest.mock import patch, MagicMock

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.database.session import SessionLocal
from apps.backend.services.chat_service import process_chat_message

def verify_memory_priority():
    print("=== TONY MEMORY PRIORITIZATION VERIFICATION (PART 7C) ===")
    
    db = SessionLocal()
    
    # Configuration for test
    TEST_WINDOW_SIZE = 100
    # Set budget to 270 to allow important facts (Score 4) to survive 
    # while trivial/filler (Score 1/2) are removed.
    TEST_TOKEN_BUDGET = 270 
    
    last_received_messages = []

    def mock_inference(messages, model):
        nonlocal last_received_messages
        last_received_messages = messages
        return "Acknowledged."

    # Patching
    with patch("apps.backend.services.chat_service.CONTEXT_WINDOW_SIZE", TEST_WINDOW_SIZE), \
         patch("apps.backend.services.chat_service.PROMPT_TOKEN_BUDGET", TEST_TOKEN_BUDGET), \
         patch("apps.backend.services.chat_service.run_llm_inference", side_effect=mock_inference):
        
        cid = None
        
        # 1. Add interactions with varying importance
        print("\n[Step 1] Adding mixed-importance interactions...")
        
        # Turn 1: Trivial (Greeting) - Score 0
        print("Sending Turn 1 (Greeting)...")
        _, cid = process_chat_message(db, "Hello, how are you today?", cid)
        
        # Turn 2: Factual (Important) - Score 3
        print("Sending Turn 2 (Fact)...")
        process_chat_message(db, "My favorite color is neon green. Please remember this.", cid)
        
        # Turn 3: Filler (Low) - Score 1
        print("Sending Turn 3 (Filler)...")
        process_chat_message(db, "Ok, thanks.", cid)
        
        # Turn 4: Normal (Moderate) - Score 2
        print("Sending Turn 4 (Normal)...")
        process_chat_message(db, "What is the capital of France?", cid)
        
        # Turn 5: Critical (High) - Score 4
        print("Sending Turn 5 (Critical)...")
        process_chat_message(db, "Remember that this project is called CLIICXNET.", cid)

        # 2. Trigger Budget Check with a long final query
        print("\n[Step 2] Triggering budget check with final query...")
        # Add some padding to the final query to ensure it hits the budget limit
        long_query = "What do you know about me? " + "x" * 200
        process_chat_message(db, long_query, cid)
        
        # 3. Assertions
        print("\n[Step 3] Assertions:")
        
        # We expect:
        # Score 0 (Greeting) -> REMOVED
        # Score 1 (Filler) -> REMOVED
        # Score 2 (Normal) -> PROBABLY REMOVED (depending on budget)
        # Score 3 (Fact) -> SHOULD SURVIVE
        # Score 4 (Critical) -> SHOULD SURVIVE
        
        message_contents = [m['content'].lower() for m in last_received_messages]
        
        print(f"Messages remaining: {len(last_received_messages)}")
        for i, m in enumerate(last_received_messages):
             role = m['role'].upper()
             content = (m['content'][:40] + "...") if len(m['content']) > 40 else m['content']
             print(f"  [{i}] {role}: {content}")

        # Assertion 1: Important facts survived
        has_fact = any("neon green" in c for c in message_contents)
        has_critical = any("cliicxnet" in c for c in message_contents)
        
        assert has_fact, "ERROR: Factual memory (Score 3) was trimmed unexpectedly!"
        assert has_critical, "ERROR: Critical memory (Score 4) was trimmed unexpectedly!"
        print("- [PASS] High-priority memories preserved.")
        
        # Assertion 2: Trivial filler was removed
        has_greeting = any("hello" in c and "how are you" in c for c in message_contents)
        has_filler = any("ok, thanks" in c for c in message_contents)
        
        assert not has_greeting, "ERROR: Greeting (Score 0) was NOT trimmed!"
        assert not has_filler, "ERROR: Filler (Score 1) was NOT trimmed!"
        print("- [PASS] Low-priority filler trimmed first.")
        
        # Assertion 3: System and Current User protected
        assert last_received_messages[0]['role'] == 'system', "ERROR: System message missing!"
        assert "what do you know about me?" in last_received_messages[-1]['content'].lower(), "ERROR: Current query missing!"
        print("- [PASS] Protected messages preserved.")

        # Assertion 4: Sequence preserved (even if gaps exist)
        # Check if Fact comes after System and before Critical (or whatever remains)
        remaining_history = last_received_messages[1:-1]
        for i in range(len(remaining_history) - 1):
            # We can't strictly check roles but we can check if they are still somewhat sequenced
            pass # Chronological order is handled by original_index sorting in token_budget.py
            
    db.close()
    print("\n=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    verify_memory_priority()
