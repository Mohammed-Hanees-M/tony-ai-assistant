import os
import sys
import json
from unittest.mock import patch, MagicMock

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.database.session import SessionLocal, engine
from apps.backend.database.base import Base
from apps.backend.services.chat_service import process_chat_message

def verify_reflective_memory():
    print("=== TONY REFLECTIVE MEMORY VERIFICATION (PART 7H) ===")
    
    # Ensure tables are created
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    captured_prompts = []
    
    def my_mock_inference(messages, model):
        system_content = messages[0]['content']
        user_content = messages[-1]['content']
        
        # Match Reflective Engine
        if "Tony's meta-cognition engine" in system_content:
            # ONLY return reflection if it's the specific Turn 1 feedback
            if "stick to Python" in user_content:
                return json.dumps({
                    "lesson": "User prefers Python for all development tasks and scripts.",
                    "context": "workflow_preference",
                    "importance": 4,
                    "is_success": True
                })
            return "NONE (No new lessons in this turn)"
            
        # Capture main Tony prompts
        if "You are Tony" in system_content and "AI assistant" in system_content:
            captured_prompts.append(messages)
            return "Main Response"
            
        return "Generic Response"

    # Patch globally across all using modules
    with patch("apps.backend.llm.inference.generate_embeddings", return_value=[0.1] * 768), \
         patch("apps.backend.services.chat_service.run_llm_inference", side_effect=my_mock_inference), \
         patch("apps.backend.llm.reflection_engine.run_llm_inference", side_effect=my_mock_inference), \
         patch("apps.backend.services.chat_service.extract_episodic_memories", return_value=None), \
         patch("apps.backend.services.chat_service.extract_long_term_memories", return_value=[]):
        
        print("\n[Step 1] Simulating behavioral preference feedback...")
        user_msg = "Hey Tony, let's stick to Python for everything."
        process_chat_message(db, user_msg, None)
        
        from apps.backend.database.models.reflection import ReflectiveMemory
        reflection = db.query(ReflectiveMemory).first()
        print(f"Reflections in DB: {db.query(ReflectiveMemory).count()}")
        print(f"Initial Confidence: {reflection.confidence} | Successes: {reflection.success_count}")
        
        print("\n[Step 2] Sending a task that follows established pattern (No new lesson)...")
        captured_prompts.clear()
        user_query = "I need a script to parse some log files."
        process_chat_message(db, user_query, None)
        
        # ASSERT: The reflection should be RECALLED
        system_msg = captured_prompts[0][0]['content']
        has_reflection = "prefers Python" in system_msg
        print(f"Reflection retrieved in prompt: {has_reflection}")
        assert has_reflection
        
        # ASSERT: The reflection SHOULD NOT have been updated (no self-reinforcement)
        db.refresh(reflection)
        print(f"Post-Task Confidence: {reflection.confidence} | Successes: {reflection.success_count}")
        
        assert reflection.success_count == 1, "ERROR: Self-reinforcement detected! Success count increased without new evidence."
        print("Verified: No self-reinforcement occurred during pattern-following task.")

    db.close()
    print("\n=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    verify_reflective_memory()
