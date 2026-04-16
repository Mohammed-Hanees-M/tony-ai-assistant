import os
import sys
from unittest.mock import patch, MagicMock

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.database.session import SessionLocal
from apps.backend.services.chat_service import process_chat_message

def verify_memory_prioritization():
    print("=== TONY MEMORY PRIORITIZATION VERIFICATION (PART 7C) ===")
    
    db = SessionLocal()
    
    # Configuration for test:
    # Character-based token estimation: len / 4
    # System prompt is ~750 chars (~188 tokens)
    # Budget must be > System Prompt + Current User Msg to keep anything.
    TEST_WINDOW_SIZE = 100
    TEST_TOKEN_BUDGET = 320 
    
    last_received_messages = []

    def mock_inference(messages, model):
        nonlocal last_received_messages
        last_received_messages = messages
        return "Acknowledged."

    # Patching config and inference
    with patch("apps.backend.services.chat_service.CONTEXT_WINDOW_SIZE", TEST_WINDOW_SIZE), \
         patch("apps.backend.services.chat_service.PROMPT_TOKEN_BUDGET", TEST_TOKEN_BUDGET), \
         patch("apps.backend.services.chat_service.run_llm_inference", side_effect=mock_inference):
        
        cid = None
        
        # 1. Add interactions with varying importance
        print("\n[Step 1] Adding mixed-importance interactions...")
        
        # Turn 1: Important Fact - Score 5
        print("Sending Turn 1 (Fact: My name is Hanees)...")
        _, cid = process_chat_message(db, "My name is Hanees. Please remember this.", cid)
        
        # Turn 2: Trivial Greeting - Score 1
        print("Sending Turn 2 (Greeting: Hello)...")
        process_chat_message(db, "Hello Tony, how are you?", cid)
        
        # Turn 3: Filler - Score 1
        print("Sending Turn 3 (Filler: Ok thanks)...")
        process_chat_message(db, "Ok, thanks for the info.", cid)
        
        # Turn 4: Normal Chat - Score 3
        print("Sending Turn 4 (Normal: Capital of France)...")
        process_chat_message(db, "What is the capital of France?", cid)
        
        # Turn 5: Important Fact - Score 5
        print("Sending Turn 5 (Fact: I love coding)...")
        process_chat_message(db, "I love coding in Python. It's my favorite language.", cid)

        # 2. Trigger Aggressive Trimming with a long final query
        print("\n[Step 2] Triggering budget check with final queries...")
        print("Asking about name (Important Fact from Turn 1)...")
        process_chat_message(db, "What is my name? Please be very detailed in your response." + "x"*400, cid)
        
        # 3. Assertions
        print("\n[Step 3] Assertions:")
        
        message_contents = [m['content'].lower() for m in last_received_messages]
        
        print(f"Messages remaining in context: {len(last_received_messages)}")
        for i, m in enumerate(last_received_messages):
             role = m['role'].upper()
             content = (m['content'][:60] + "...") if len(m['content']) > 60 else m['content']
             print(f"  [{i}] {role}: {content}")

        # Assertion 1: Important facts survived (Hanees)
        has_name = any("hanees" in c for c in message_contents)
        has_language = any("python" in c for c in message_contents)
        
        assert has_name, "ERROR: Important fact 'Hanees' (Score 5) was trimmed unexpectedly!"
        assert has_language, "ERROR: Important fact 'Python' (Score 5) was trimmed unexpectedly!"
        print("- [PASS] High-priority memories preserved.")
        
        # Assertion 2: Trivial filler was removed first
        has_greeting = any("hello tony" in c for c in message_contents)
        has_filler = any("ok, thanks" in c for c in message_contents)
        
        assert not has_greeting, "ERROR: Greeting (Score 1) was NOT trimmed!"
        assert not has_filler, "ERROR: Filler (Score 1) was NOT trimmed!"
        print("- [PASS] Low-priority trivial/filler messages trimmed first.")
        
        # Assertion 3: System and Current User protected
        assert last_received_messages[0]['role'] == 'system', "ERROR: System message missing!"
        assert "what is my name?" in last_received_messages[-1]['content'].lower(), "ERROR: Current query missing!"
        print("- [PASS] Protected messages preserved.")

        # Assertion 4: Pair-safe trimming
        # Ensure we have even number of historical messages (system excluded, user query excluded)
        history_len = len(last_received_messages) - 2
        assert history_len % 2 == 0, f"ERROR: Trimming was not pair-safe! History length: {history_len}"
        print("- [PASS] Pair-safe trimming verified.")

    db.close()
    print("\n=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    verify_memory_prioritization()
