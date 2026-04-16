import os
import sys
from unittest.mock import patch, MagicMock

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.database.session import SessionLocal, engine
from apps.backend.database.base import Base
from apps.backend.services.chat_service import process_chat_message

def verify_episodic_memory():
    print("=== TONY EPISODIC MEMORY VERIFICATION (PART 7G) ===")
    
    # Ensure tables are created
    Base.metadata.drop_all(bind=engine) # FORCED RESET FOR TEST ISOLATION
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    from apps.backend.database.models.episode import EpisodicMemory
    initial_count = db.query(EpisodicMemory).count()
    print(f"[PRE-TEST] Initial episodic memory count: {initial_count}")
    assert initial_count == 0, "ERROR: Database not clean before verification."

    last_prompt = []
    def mock_inference(messages, model):
        nonlocal last_prompt
        last_prompt = messages
        # If the prompt is for episodic extraction (contains "Tony's experience logger"), return JSON
        system_content = messages[0]['content']
        if "Tony's experience logger" in system_content:
            return json.dumps({
                "event_type": "task_completion",
                "summary": "Finished implementing the episodic memory layer",
                "outcome": "Success, experience engine is operational",
                "importance": 5,
                "tags": "episodic, memory, dev"
            })
        return "Acknowledged."

    import json
    # Patch inference
    with patch("apps.backend.services.chat_service.run_llm_inference", side_effect=mock_inference):
        
        print("\n[Step 1] Simulating a task completion event...")
        conv_id_1 = None
        user_msg = "I finally finished implementing the episodic memory layer today."
        # Capture stdout to verify NO experiences are retrieved yet
        from io import StringIO
        import sys as system_sys
        old_stdout = system_sys.stdout
        result_out = StringIO()
        system_sys.stdout = result_out
        
        try:
            _, conv_id_1 = process_chat_message(db, user_msg, conv_id_1)
        finally:
            system_sys.stdout = old_stdout
            
        logs = result_out.getvalue()
        print(logs)
        
        assert "Retrieved" not in logs, "ERROR: Experiences retrieved even though DB should be empty."
        print("Verified: No past experiences retrieved before first event stored.")
        
        # Verify it was captured
        post_step1_count = db.query(EpisodicMemory).count()
        print(f"Post-Step 1 episodic memory count: {post_step1_count}")
        assert post_step1_count == 1, "ERROR: New episodic memory not stored."

        print("\n[Step 2] Starting fresh conversation and asking about recent progress...")
        last_prompt = [] # Reset
        user_query = "What did we recently do regarding the memory system?"
        process_chat_message(db, user_query, None) # New conversation
        
        system_msg = last_prompt[0]['content']
        print(f"Prompt Header Check: 'PAST RELEVANT EXPERIENCES' in prompt: {'PAST RELEVANT EXPERIENCES' in system_msg}")
        
        has_episode = "episodic memory layer" in system_msg
        print(f"Recent experience found in prompt: {has_episode}")
        
        assert has_episode, "ERROR: Episodic memory was not retrieved or injected into new conversation."

    db.close()
    print("\n=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    verify_episodic_memory()
