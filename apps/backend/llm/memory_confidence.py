from datetime import datetime, timezone

def assign_initial_confidence(memory, source_type: str = "explicit"):
    """
    Assign initial confidence score based on the source of the memory.
    """
    memory.confidence_source = source_type
    
    # Confidence defaults
    scores = {
        "explicit": 0.90,       # Explicit user fact: 0.85-0.95
        "correction": 0.95,     # Explicit correction: 0.95+
        "extraction": 0.70,     # Inferred fact: 0.50-0.75
        "reflection": 0.80,     # Reflective lesson: medium-high
        "episodic": 0.65        # Episodic summary: medium
    }
    
    memory.confidence_score = scores.get(source_type, 0.70)
    memory.last_confidence_update = datetime.now(timezone.utc)
    print(f"[CONFIDENCE] '{getattr(memory, 'key', getattr(memory, 'summary', getattr(memory, 'lesson', 'memory')))}' assigned {memory.confidence_score:.2f} ({source_type})")
    return memory

def reinforce_confidence(memory):
    """
    Modestly reinforce confidence on successful retrieval/use.
    Cap at 1.0.
    """
    old_score = getattr(memory, 'confidence_score', 0.70)
    if old_score is None: old_score = 0.70
    new_score = min(1.0, old_score + 0.05)
    memory.confidence_score = new_score
    memory.last_confidence_update = datetime.now(timezone.utc)
    print(f"[CONFIDENCE] '{getattr(memory, 'key', getattr(memory, 'summary', getattr(memory, 'lesson', 'memory')))}' reinforced: {old_score:.2f} -> {new_score:.2f}")
    return memory

def reduce_confidence(memory, amount=0.15):
    """
    Reduce confidence explicitly due to contradictions/supersession.
    Repeated corrections lower confidence of prior chain.
    """
    old_score = getattr(memory, 'confidence_score', 0.70)
    if old_score is None: old_score = 0.70
    new_score = max(0.0, old_score - amount)
    memory.confidence_score = new_score
    memory.last_confidence_update = datetime.now(timezone.utc)
    print(f"[CONFIDENCE] '{getattr(memory, 'key', getattr(memory, 'summary', getattr(memory, 'lesson', 'memory')))}' reduced: {old_score:.2f} -> {new_score:.2f}")
    return memory

def recompute_confidence(memory):
    """
    Recompute confidence based on access count, reinforcement count, and failures.
    Placeholder for future probabilistic reasoning.
    """
    base = getattr(memory, 'confidence_score', 0.70)
    if base is None: base = 0.70
    success = getattr(memory, 'success_count', 0)
    failure = getattr(memory, 'failure_count', 0)
    reinforcements = getattr(memory, 'reinforcement_count', 0)
    
    adjustment = (reinforcements * 0.01) + (success * 0.02) - (failure * 0.05)
    new_score = max(0.0, min(1.0, base + adjustment))
    
    if abs(new_score - base) > 0.01:
        print(f"[CONFIDENCE] '{getattr(memory, 'key', getattr(memory, 'summary', getattr(memory, 'lesson', 'memory')))}' recomputed: {base:.2f} -> {new_score:.2f}")
        memory.confidence_score = new_score
        memory.last_confidence_update = datetime.now(timezone.utc)
        
    return memory
