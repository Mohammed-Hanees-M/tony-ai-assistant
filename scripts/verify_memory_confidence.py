import os
import sys
import json
from unittest.mock import patch

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.database.models.memory import LongTermMemory
from apps.backend.llm.memory_confidence import (
    assign_initial_confidence,
    reinforce_confidence,
    reduce_confidence
)
from apps.backend.llm.memory_retriever import compute_rerank_score
from apps.backend.llm.prompt_manager import build_messages

def run_verification():
    print("=== TONY MEMORY CONFIDENCE VERIFICATION (PART 7K) ===\n")
    
    # A. Explicit facts start high-confidence
    mem_explicit = LongTermMemory(key="user_name", value="John Doe")
    assign_initial_confidence(mem_explicit, "explicit")
    print(f"Test A: Explicit Memory confidence: {mem_explicit.confidence_score} (Expected ~0.90)")
    assert mem_explicit.confidence_score >= 0.85, "Explicit memory confidence too low"

    # B. Inferred facts start lower
    mem_inferred = LongTermMemory(key="user_hobby", value="Likes chess based on previous match mention")
    assign_initial_confidence(mem_inferred, "extraction")
    print(f"Test B: Inferred Memory confidence: {mem_inferred.confidence_score} (Expected ~0.70)")
    assert mem_inferred.confidence_score <= 0.75, "Inferred memory confidence too high"

    # C. Reinforcement raises confidence
    initial_conf = mem_inferred.confidence_score
    reinforce_confidence(mem_inferred)
    print(f"Test C: Reinforced Inferred Memory: {initial_conf:.2f} -> {mem_inferred.confidence_score:.2f}")
    assert mem_inferred.confidence_score > initial_conf, "Reinforcement did not raise confidence"

    # D. Corrections reduce prior memory confidence
    conf_before_reduce = mem_explicit.confidence_score
    reduce_confidence(mem_explicit, 0.20)
    print(f"Test D: Reduced Explicit Memory: {conf_before_reduce:.2f} -> {mem_explicit.confidence_score:.2f}")
    assert mem_explicit.confidence_score < conf_before_reduce, "Reduction did not lower confidence"

    # E. Retrieval ranks higher-confidence memory above lower-confidence alternatives
    # Both have identical similarity and keywords
    sim_score = 0.8
    query = "Hobby"
    intents = []
    
    # Set explicit confidence difference
    mem_high_conf = LongTermMemory(key="hobby", value="Chess", confidence_score=0.95, strength_score=1.0)
    mem_low_conf = LongTermMemory(key="hobby", value="Checkers", confidence_score=0.30, strength_score=1.0)
    
    score_high = compute_rerank_score(query, mem_high_conf, sim_score, intents)
    score_low = compute_rerank_score(query, mem_low_conf, sim_score, intents)
    
    print(f"\nTest E Ranking Comparison:")
    print(f"  - High Conf (0.95) Final Score: {score_high['final_score']:.4f}")
    print(f"  - Low Conf (0.30) Final Score: {score_low['final_score']:.4f}")
    assert score_high['final_score'] > score_low['final_score'], "Retrieval failed to rank high-confidence over low-confidence"

    # F. Low-confidence memories flagged in prompt
    print(f"\nTest F: Low-confidence framing in Prompt Manager")
    
    lt_memories = [
        {"key": "confident_fact", "value": "User likes Python", "confidence": 0.95},
        {"key": "unsure_fact", "value": "User might know Rust", "confidence": 0.40}
    ]
    
    context = {
        "message": "Hello",
        "long_term_memories": lt_memories
    }
    
    messages = build_messages(context)
    system_prompt = messages[0]["content"]
    
    print(f"\nExtracted relevant prompt block:")
    import re
    mem_block = re.search(r"LONG-TERM MEMORY.*?:\n(.*)", system_prompt, re.DOTALL)
    if mem_block:
        print(mem_block.group(0))
        
    assert "(Low Confidence Memory)" in system_prompt, "Flag missing from prompt"
    assert system_prompt.count("(Low Confidence Memory)") == 1, "Flag applied incorrectly"
    print("\nVerified: Low-confidence fact correctly flagged in prompt, high-confidence fact unflagged.")

    print("\n=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    run_verification()
