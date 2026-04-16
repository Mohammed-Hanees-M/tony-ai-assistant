import os
import sys

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.llm.token_budget import trim_messages_to_token_budget, estimate_tokens
from apps.backend.core.config import PROMPT_TOKEN_BUDGET

def verify_token_budgeting():
    print("=== TONY TOKEN BUDGETING VERIFICATION ===")
    print(f"Target Budget: {PROMPT_TOKEN_BUDGET} tokens.")
    
    # Test Case 1: Oversized messages
    # Each character is ~0.25 tokens. To get ~1000 tokens, we need 4000 chars.
    large_content = "X" * 4000 # ~1000 tokens
    
    messages = [
        {"role": "system", "content": "You are Tony."}, # ~4 tokens
        {"role": "user", "content": large_content},      # ~1000 tokens
        {"role": "assistant", "content": large_content}, # ~1000 tokens
        {"role": "user", "content": large_content},      # ~1000 tokens
        {"role": "assistant", "content": large_content}, # ~1000 tokens
        {"role": "user", "content": "Tell me a joke."}   # current user message (~3 tokens)
    ]
    
    initial_tokens = sum(estimate_tokens(m["content"]) for m in messages)
    print(f"\nInitial message list size: {len(messages)}")
    print(f"Initial estimated tokens: {initial_tokens}")
    
    # Apply trimming
    trimmed_messages = trim_messages_to_token_budget(messages, PROMPT_TOKEN_BUDGET)
    
    final_tokens = sum(estimate_tokens(m["content"]) for m in trimmed_messages)
    print(f"\nFinal message list size: {len(trimmed_messages)}")
    print(f"Final estimated tokens: {final_tokens}")
    
    # Assertions
    assert final_tokens <= PROMPT_TOKEN_BUDGET, f"Final tokens {final_tokens} exceeds budget {PROMPT_TOKEN_BUDGET}!"
    assert trimmed_messages[0]["role"] == "system", "System message was removed!"
    assert trimmed_messages[-1]["content"] == "Tell me a joke.", "Current user message was removed!"
    assert len(trimmed_messages) < len(messages), "No messages were removed even though we were over budget!"
    
    print("\n[Audit] Preserved Messages:")
    for i, m in enumerate(trimmed_messages):
        print(f"  [{i}] {m['role'].upper()}: {len(m['content'])} chars (~{estimate_tokens(m['content'])} tokens)")

    print("\nVERIFICATION SUCCESSFUL: Token budgeting engine is working correctly.")

if __name__ == "__main__":
    verify_token_budgeting()
