import os
import sys
from unittest.mock import patch, MagicMock

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.database.session import SessionLocal, engine
from apps.backend.database.base import Base
from apps.backend.services.chat_service import process_chat_message
from apps.backend.database.repositories.summary_repository import get_all_summaries

def verify_memory_summarization():
    print("=== TONY MEMORY SUMMARIZATION VERIFICATION (PART 7F) ===")
    
    # Ensure tables are created (including new summary table)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    last_prompt = []
    def mock_inference(messages, model):
        nonlocal last_prompt
        last_prompt = messages
        return f"Acknowledged msg."

    # Patch inference
    with patch("apps.backend.services.chat_service.run_llm_inference", side_effect=mock_inference):
        
        print("\n[Step 1] Creating a long conversation to trigger summarization threshold (15)...")
        conv_id = None
        for i in range(16):
            msg = f"Message number {i+1}: Testing memory flow."
            _, conv_id = process_chat_message(db, msg, conv_id)
            
            # Check if summarization happened (usually after the 15th message is saved)
            summaries = get_all_summaries(db, conv_id)
            if summaries:
                print(f"[EVENT] Summarization triggered at message {i+1}!")
                break
        
        # Verify summary in DB
        summaries = get_all_summaries(db, conv_id)
        assert len(summaries) > 0, "ERROR: No summary found in database after exceeding threshold."
        summary_text = summaries[0].summary_text
        print(f"Verified: {len(summaries)} summary record(s) found.")
        print(f"Summary Content: {summary_text[:100]}...")

        # Hallucination Check: CLIICXNET was not in the input messages
        if "CLIICXNET" in summary_text.upper():
            print("[CRITICAL] Hallucination Detected: 'CLIICXNET' found in summary but absent from source chunk.")
            # We fail the test if hallucination found
            assert "CLIICXNET" not in summary_text.upper(), "ERROR: Summary includes hallucinated external context."
        else:
            print("Verified: No hallucinated project references found.")

        # Step 2: Verify Prompt Injection
        print("\n[Step 2] Verifying summary injection into system prompt...")
        process_chat_message(db, "What was my first message?", conv_id)
        
        system_msg = last_prompt[0]['content']
        has_summary_header = "CONVERSATION SUMMARY (PAST CONTEXT):" in system_msg
        print(f"Summary header found in prompt: {has_summary_header}")
        
        assert has_summary_header, "ERROR: Summary not found in system prompt."

        # Step 3: Verify recall of summarized context
        # Since we mocked inference, we can't test "Tony's" recall directly in this script,
        # but we proved the context is there.
        
    db.close()
    print("\n=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    verify_memory_summarization()
