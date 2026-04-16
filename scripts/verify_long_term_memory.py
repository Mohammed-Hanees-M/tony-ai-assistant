import os
import sys
from unittest.mock import patch

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.database.session import SessionLocal, engine
from apps.backend.database.base import Base
from apps.backend.database.repositories.memory_repository import get_top_memories
from apps.backend.services.chat_service import process_chat_message

def verify_long_term_memory():
    print("=== TONY LONG-TERM MEMORY VERIFICATION (PART 7D) ===")
    
    # Ensure tables are created
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    last_received_messages = []
    def mock_inference(messages, model):
        nonlocal last_received_messages
        last_received_messages = messages
        return "Acknowledged."

    # Use a tight prompt budget to show it's separate from history
    with patch("apps.backend.services.chat_service.run_llm_inference", side_effect=mock_inference), \
         patch("apps.backend.services.chat_service.PROMPT_TOKEN_BUDGET", 300):
        
        # 1. Store Facts (Refined Policy Test)
        print("\n[Step 1] Storing facts under refined policy...")
        
        # A. Automatic Structured Facts
        print("Sending automatic facts (Identity/Project)...")
        process_chat_message(db, "My name is Hanees.")
        process_chat_message(db, "I am working on a secret AI named Tony.")
        
        # B. Generic Fact WITHOUT Directive (Should NOT be saved)
        print("Sending generic fact WITHOUT directive (Should be ignored)...")
        process_chat_message(db, "The server address is 192.168.1.50")
        
        # C. Generic Fact WITH Directive (Should BE saved)
        print("Sending generic fact WITH directive (Should be saved)...")
        process_chat_message(db, "Save this: the API endpoint is https://api.tony.com")
        process_chat_message(db, "Don't forget the meeting is at 5 PM tomorrow.")

        # D. Sensitive Data WITH Directive (Should be BLOCKED)
        print("Sending sensitive data WITH directive (Should be BLOCKED)...")
        process_chat_message(db, "Save this: the secret server password is secret123")
        process_chat_message(db, "Remember that my API key is ABC-123-XYZ")

        # 2. Verifying memory state
        print("\n[Step 2] Verifying memory state in DB...")
        memories = get_top_memories(db, limit=10)
        print(f"Total memories in DB: {len(memories)}")
        for m in memories:
            print(f"  - {m.key}: {m.value}")

        # 3. Start a New Conversation
        print("\n[Step 3] Starting a fresh second conversation...")
        cid = None 
        
        # 4. Final Query
        print("\n[Step 4] Querying Tony in the second conversation...")
        process_chat_message(db, "What are the server details and project info?", cid)
        
        # 5. Assertions
        print("\n[Step 5] Assertions:")
        
        system_msg = last_received_messages[0]['content']
        
        # Check if LTMs are in System Message correctly
        has_name = "user_name: Hanees" in system_msg 
        has_project = "project_context: a secret ai named tony" in system_msg
        has_endpoint = "api endpoint is https://api.tony.com" in system_msg
        has_meeting = "the meeting is at 5 pm tomorrow" in system_msg
        
        # Check SECURITY case: sensitive data should NOT be here
        has_password = "password" in system_msg.lower() or "secret123" in system_msg
        has_apikey = "api key" in system_msg.lower() or "abc-123-xyz" in system_msg
        
        # Check NEGATIVE case: server address from Step 1 B should NOT be here
        has_server = "192.168.1.50" in system_msg
        
        print("\nDebug - System Message Section (LTM):")
        if "LONG-TERM MEMORY" in system_msg:
            print(system_msg[system_msg.find("LONG-TERM MEMORY"):])
        else:
            print("LONG-TERM MEMORY SECTION NOT FOUND!")

        assert has_name, "ERROR: Automatic Identity fact missing!"
        assert has_project, "ERROR: Automatic Project fact missing!"
        assert has_endpoint, "ERROR: Non-sensitive directive-based fact missing!"
        assert has_meeting, "ERROR: Non-sensitive directive-based fact missing!"
        
        assert not has_password, "ERROR: Sensitive data (Password) was incorrectly persisted!"
        assert not has_apikey, "ERROR: Sensitive data (API Key) was incorrectly persisted!"
        assert not has_server, "ERROR: Generic fact WITHOUT directive was incorrectly persisted!"

        print("- [PASS] Security Verified: Sensitive data blocked correctly.")

    db.close()
    print("\n=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    verify_long_term_memory()
