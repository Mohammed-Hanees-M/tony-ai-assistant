import os
import sys
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.database.session import SessionLocal
from apps.backend.services.chat_service import process_chat_message

def verify_token_budgeting():
    print("=== TONY TOKEN BUDGETING VERIFICATION (PART 7B) ===")
    
    db = SessionLocal()
    
    # Configuration for test
    TEST_WINDOW_SIZE = 100 # Large window to allow many messages through
    TEST_TOKEN_BUDGET = 200 # Small budget to trigger trimming (approx 800 chars / 4)
    
    last_received_messages = []

    def mock_inference(messages, model):
        nonlocal last_received_messages
        last_received_messages = messages
        print(f"[VERIFY] Mock Inference received {len(messages)} messages.")
        # Return a standard response
        return "Acknowledged. I have recorded this fact."

    # Patching
    with patch("apps.backend.services.chat_service.CONTEXT_WINDOW_SIZE", TEST_WINDOW_SIZE), \
         patch("apps.backend.services.chat_service.PROMPT_TOKEN_BUDGET", TEST_TOKEN_BUDGET), \
         patch("apps.backend.services.chat_service.run_llm_inference", side_effect=mock_inference):
        
        print(f"Config Override: CONTEXT_WINDOW_SIZE={TEST_WINDOW_SIZE}, PROMPT_TOKEN_BUDGET={TEST_TOKEN_BUDGET}")
        
        # 1. Add several large facts to exceed the budget
        print("\n[Step 1] Adding 5 large facts to exceed token budget...")
        cid = None
        # Each fact is purposefully long (~300 chars)
        facts = [
            "Fact A: " + "a" * 300,
            "Fact B: " + "b" * 300,
            "Fact C: " + "c" * 300,
            "Fact D: " + "d" * 300,
            "Fact E: " + "e" * 300
        ]
        
        for i, fact in enumerate(facts):
            print(f"Sending Fact {chr(65+i)}...")
            process_chat_message(db, fact, cid)
            # Fetch CID if it was None
            if cid is None:
                from apps.backend.database.repositories.conversation_repository import get_recent_messages
                # Get the most recent conversation created in this session (simplified for test)
                from apps.backend.database.models.conversation import Conversation
                conv = db.query(Conversation).order_by(Conversation.id.desc()).first()
                cid = conv.id
        
        print(f"\n[Step 2] Sending final query to trigger budget check...")
        process_chat_message(db, "What was Fact A?", cid)
        
        # 2. Assertions
        print("\n[Step 3] Assertions:")
        
        # The last messages received by inference should be trimmed
        # Each fact (U+A) is ~300 chars, so ~75 tokens + assistant reply tokens.
        # Total tokens for 5 facts + System + Current = ~400-500 tokens.
        # TEST_TOKEN_BUDGET = 200.
        # So it MUST trigger trimming.
        
        # 1. Confirm token budget overflow occurred (log-based check via side effect or examining state)
        # We can detect trimming if length of last_received_messages < expected total.
        # Expected total = 1 (System) + 10 (5 U+A pairs) + 1 (Current User Message) = 12
        actual_count = len(last_received_messages)
        print(f"Messages received by inference: {actual_count} (Expected < 12 if trimming worked)")
        
        assert actual_count < 12, "ERROR: Token budget trimming never activated!"
        print("- [PASS] Token budget overflow occurred and trimming activated.")
        
        # 2. Confirm pair-safe trimming occurs
        # If trimming preserves pairs, then current_messages[1] should be a 'user' message 
        # and current_messages[2] should be 'assistant', or similar structure.
        # Specifically, the system message at [0] and current user at [-1] must remain.
        # The history messages in between should be in pairs.
        
        for i in range(1, len(last_received_messages) - 1, 2):
            role1 = last_received_messages[i]['role']
            role2 = last_received_messages[i+1]['role']
            assert role1 == 'user' and role2 == 'assistant', f"ERROR: Orphaned message detected at index {i}/{i+1}: {role1}/{role2}"
        print("- [PASS] Pair-safe trimming confirmed (No orphaned assistant messages).")
        
        # 3. Confirm protected messages remain
        assert last_received_messages[0]['role'] == 'system', "ERROR: System message was trimmed!"
        assert last_received_messages[-1]['role'] == 'user', "ERROR: Current user message was trimmed!"
        assert "What was Fact A?" in last_received_messages[-1]['content'], "ERROR: Current query is incorrect!"
        print("- [PASS] Protected messages (System message & Current User message) preserved.")
        
        # 4. Confirm trimmed memory is forgotten
        # Fact A should definitely be trimmed as it's the oldest.
        fact_a_content_present = any("Fact A: aaaaa" in msg['content'] for msg in last_received_messages)
        assert not fact_a_content_present, "ERROR: Fact A content was NOT trimmed but it should have been!"
        print("- [PASS] Trimmed memory content is forgotten by Tony.")

    db.close()
    print("\n=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    verify_token_budgeting()
