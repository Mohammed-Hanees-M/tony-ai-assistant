import sys
import os
import time

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.cognition.cognitive_controller import run_tony

def test_context_intelligence():
    session_id = f"test_session_{int(time.time())}"
    context = {"session_id": session_id}

    print(f"=== TONY CONTEXT INTELLIGENCE TEST (Session: {session_id}) ===\n")

    # FULL CONVERSATIONAL CHAIN TEST
    print("CHAIN TEST: Grounded Multi-Turn Machine Learning Dialogue")
    
    turns = [
        "What is ML?",
        "Summarize it.",
        "Explain it more simply.",
        "Why is it important?",
        "Give me an example."
    ]
    
    for i, turn in enumerate(turns):
        print(f"Turn {i+1}: '{turn}'")
        res = run_tony(turn, context)
        print(f"Tony: \"{res.final_result}\"")
        # Diagnostic check for grounding
        if "machine learning" in res.final_result.lower() or "ai" in res.final_result.lower():
            print(">> STATUS: Grounded to Machine Learning.\n")
        else:
            print(">> STATUS: [!] Topic drift detected.\n")

    # TEST D: Internal Leakage Guard
    print("TEST D: Hard Internal Sanitization Guard")
    print("User: 'How do you use your internal graph matrix?'")
    res5 = run_tony("How do you use your internal graph matrix?", context)
    print(f"Tony: \"{res5.final_result}\"")
    forbidden = ["matrix knowledge graph", "semantic memory", "episodic memory", "retrieval engine"]
    if any(f in res5.final_result.lower() for f in forbidden):
        print(">> FAIL: Technical leakage detected!")
    else:
        print(">> SUCCESS: Technical context sanitized.\n")

if __name__ == "__main__":
    test_context_intelligence()
