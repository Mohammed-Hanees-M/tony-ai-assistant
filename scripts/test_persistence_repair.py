import os
import sys
from unittest.mock import patch

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.database.session import SessionLocal
from apps.backend.services.chat_service import process_chat_message
from apps.backend.database.repositories.conversation_repository import get_messages

def verify_persistence_repair():
    db = SessionLocal()
    print("=== TONY PERSISTENCE REPAIR VERIFICATION ===")
    
    # Use a real CID but mock the result
    test_cid = None
    
    # 1. Test Success Path
    print("\n[Test-1] Testing Success Path...")
    with patch("apps.backend.services.chat_service.run_llm_inference") as mock_inference:
        mock_inference.return_value = "This is a successful response."
        
        response, cid = process_chat_message(db, "Success query", None)
        test_cid = cid
        
        # Verify persistence
        messages = get_messages(db, cid)
        user_persisted = any(m.content == "Success query" for m in messages)
        assistant_persisted = any(m.content == "This is a successful response." for m in messages)
        
        print(f"User message persisted: {user_persisted}")
        print(f"Assistant message persisted: {assistant_persisted}")
        assert user_persisted and assistant_persisted, "Success path failed to persist messages!"

    # 2. Test Failure Path
    print("\n[Test-2] Testing Failure Path...")
    with patch("apps.backend.services.chat_service.run_llm_inference") as mock_inference:
        mock_inference.return_value = "[Error] Ollama inference failed: 500 Server Error"
        
        response, cid = process_chat_message(db, "Failure query", test_cid)
        
        # Verify non-persistence
        messages = get_messages(db, test_cid)
        # We check if "Failure query" or the error string is in the DB
        failure_user_in_db = any(m.content == "Failure query" for m in messages)
        error_string_in_db = any("[Error]" in m.content for m in messages)
        
        print(f"Failure query in DB: {failure_user_in_db}")
        print(f"Error string in DB: {error_string_in_db}")
        
        assert not failure_user_in_db, "Failure query was persisted!"
        assert not error_string_in_db, "Error message was persisted!"
        assert response.startswith("[Error]"), "Returned response was not the expected error string"

    print("\nVERIFICATION SUCCESSFUL: Failed inference no longer pollutes DB history.")
    db.close()

if __name__ == "__main__":
    verify_persistence_repair()
