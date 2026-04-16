import os
import sys

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.llm.token_budget import trim_messages_to_token_budget, estimate_tokens
from apps.backend.core.config import PROMPT_TOKEN_BUDGET

def verify_coherence():
    print("=== TONY CONVERSATIONAL INTEGRITY AUDIT ===")
    print(f"Target Budget: {PROMPT_TOKEN_BUDGET} tokens.")
    
    # Each character is ~0.25 tokens. 
    # Turn 1: U1 + A1 (~1000 + ~1000 = ~2000 tokens)
    # Turn 2: U2 + A2 (~1000 + ~1000 = ~2000 tokens)
    # Total history: ~4000 tokens (OVER BUDGET)
    
    large_u1 = "U1" + "X" * 3998 # ~1000 tokens
    large_a1 = "A1" + "X" * 3998 # ~1000 tokens
    large_u2 = "U2" + "X" * 3998 # ~1000 tokens
    large_a2 = "A2" + "X" * 3998 # ~1000 tokens
    
    messages = [
        {"role": "system", "content": "System message."}, # ~4 tokens
        {"role": "user", "content": large_u1},           # ~1000 tokens
        {"role": "assistant", "content": large_a1},      # ~1000 tokens
        {"role": "user", "content": large_u2},           # ~1000 tokens
        {"role": "assistant", "content": large_a2},      # ~1000 tokens
        {"role": "user", "content": "Current question."} # current user message (~4 tokens)
    ]
    
    initial_tokens = sum(estimate_tokens(m["content"]) for m in messages)
    print(f"\nInitial message list size: {len(messages)}")
    print(f"Initial estimated tokens: {initial_tokens}")
    
    # Scenario: Trimming should remove U1+A1 together.
    # Current question + System + U2 + A2 = ~2008 tokens. This is UNDER 3072.
    # If it removes only U1, tokens = ~3008. (Under budget, but A1 remains alone!).
    # My new logic should remove BOTH U1 and A1.
    
    trimmed_messages = trim_messages_to_token_budget(messages, PROMPT_TOKEN_BUDGET)
    
    final_tokens = sum(estimate_tokens(m["content"]) for m in trimmed_messages)
    print(f"\nFinal message list size: {len(trimmed_messages)}")
    print(f"Final estimated tokens: {final_tokens}")
    
    # Assertions
    assert final_tokens <= PROMPT_TOKEN_BUDGET, f"Final tokens {final_tokens} exceeds budget!"
    assert trimmed_messages[0]["role"] == "system", "System message removed!"
    assert trimmed_messages[-1]["content"] == "Current question.", "Current message removed!"
    
    # Coherence Check:
    # After removing oldest turn (U1, A1), the first history message (at index 1) should be U2.
    assert trimmed_messages[1]["content"].startswith("U2"), f"Expected U2 at index 1, but found {trimmed_messages[1]['role']} starts with {trimmed_messages[1]['content'][:5]}"
    
    print("\n[Audit] Preserved History Structure:")
    for i, m in enumerate(trimmed_messages):
        print(f"  [{i}] {m['role'].upper()}: {m['content'][:10]}...")

    print("\nVERIFICATION SUCCESSFUL: Conversational integrity maintained. Old turns removed in pairs.")

if __name__ == "__main__":
    verify_coherence()
