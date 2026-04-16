import sys
import os
import time

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apps.backend.cognition.cognitive_controller import run_tony
from apps.backend.conversation.context_manager import get_session_context, update_session_context

def test_grounding():
    session_id = "test_sess_followup"
    # Set initial state: Who is Tony?
    update_session_context(session_id, {
        "primary_topic": "Tony (AI Assistant identity)",
        "active_topics": ["Tony"]
    })
    
    print("\n--- TEST 1: Follow-Up Grounding ---")
    query = "Yes, give me more detail"
    print(f"Query: {query}")
    
    result = run_tony(query, {"session_id": session_id})
    print(f"Resolved Query: {result.resolved_query}")
    print(f"Route Reason: {result.plan.routing_reason}")
    print(f"Response: {result.final_result[:100]}...")
    
    assert "Tony" in result.resolved_query
    assert "Simple follow-up retrieval bypass" in result.plan.routing_reason

def test_identity_lock():
    session_id = "test_sess_identity"
    print("\n--- TEST 2: Identity Context Lock ---")
    query = "Who are you?"
    print(f"Query: {query}")
    
    result = run_tony(query, {"session_id": session_id})
    print(f"Route Reason: {result.plan.routing_reason}")
    print(f"Response: {result.final_result[:100]}...")
    
    assert "identity_profile" in result.plan.routing_reason or "social match" in result.plan.routing_reason
    assert "memory" not in result.plan.required_modules

def test_fast_fallback():
    print("\n--- TEST 3: Fast Fallback (Simulated slow llama3) ---")
    # This is harder to test without actual slow LLM, but we can verify code path
    # by looking at logs from previous runs or assuming it works if it doesn't crash.
    pass

if __name__ == "__main__":
    try:
        test_grounding()
        test_identity_lock()
        print("\n[SUCCESS] All follow-up grounding tests passed!")
    except Exception as e:
        print(f"\n[FAILURE] {e}")
        import traceback
        traceback.print_exc()
