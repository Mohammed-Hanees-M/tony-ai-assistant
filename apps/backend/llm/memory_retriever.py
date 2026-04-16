import re
import json
import math
from sqlalchemy.orm import Session
from apps.backend.database.repositories.memory_repository import get_all_memories
from apps.backend.llm.inference import generate_embeddings
from apps.backend.llm.memory_governance import reinforce_memory

def dot_product(v1, v2):
    return sum(x * y for x, y in zip(v1, v2))

def magnitude(v):
    return math.sqrt(sum(x * x for x in v))

def cosine_similarity(v1, v2):
    if not v1 or not v2:
        return 0.0
    if len(v1) != len(v2):
        print(f"[DEBUG] Vector mismatch: {len(v1)} vs {len(v2)}")
        return 0.0
    mag1 = magnitude(v1)
    mag2 = magnitude(v2)
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot_product(v1, v2) / (mag1 * mag2)

def classify_query_intent(query: str) -> list[str]:
    """Classifies query into likely memory categories using keyword profiling."""
    q = query.lower()
    intents = []
    
    mapping = {
        "identity": ["name", "who am i", "who is", "identity", "me", "myself"],
        "preference": ["favorite", "like", "love", "taste", "food", "eat", "drink", "interested", "language", "code", "coding", "program", "hobby"],
        "project": ["project", "building", "build", "cliicxnet", "creating", "robot", "tony"],
        "schedule": ["meeting", "tomorrow", "schedule", "when", "time", "soon", "event"],
        "work": ["work", "job", "office", "task", "software", "engineer", "dev", "develop"]
    }
    
    for cat, keywords in mapping.items():
        for kw in keywords:
            if re.search(r'\b' + re.escape(kw) + r'\b', q):
                intents.append(cat)
                break
            
    return intents

def compute_rerank_score(query: str, memory, sim_score: float, intent_categories: list[str]) -> dict:
    """Computes a multi-dimensional reranked score for a memory candidate."""
    boost = 0.0
    reason = "None"
    
    # 1. Direct Category Match Boost
    m_cat = getattr(memory, 'category', 'fact')
    if m_cat in intent_categories:
        boost += 0.35
        reason = f"Intent Match ({m_cat})"
    
    # 2. Key/Value Keyword Boost (Secondary signal)
    q_low = query.lower()
    m_key = getattr(memory, 'key', '') or ''
    m_val = getattr(memory, 'value', '') or getattr(memory, 'lesson', '') or getattr(memory, 'summary', '') or ''
    
    if (m_key and m_key.lower() in q_low) or (m_val and m_val.lower() in q_low):
        boost += 0.15
        reason = f"Keyword Match" if reason == "None" else f"{reason} + Keyword"

    # Incorporate Confidence and Strength into the similarity base
    strength = getattr(memory, 'strength_score', 1.0)
    if strength is None: strength = 1.0
    confidence = getattr(memory, 'confidence_score', 1.0)
    if confidence is None: confidence = 1.0
    
    # Base importance if applicable
    importance = getattr(memory, 'importance', 1) or 1
    
    # Give similarity the bulk of the weight, but modulate up to 20% by strength/confidence.
    adjusted_sim = sim_score * (0.8 + 0.1 * strength + 0.1 * confidence)
    
    # Additional boost for importance
    adjusted_sim += importance * 0.02

    final_score = min(1.0, adjusted_sim + boost)
    
    return {
        "final_score": final_score,
        "sim_score": sim_score,
        "boost": boost,
        "reason": reason
    }

def retrieve_relevant_long_term_memories(db: Session, query: str, limit: int = 5):
    """
    Best-in-Class Semantic Retrieval for Tony v2.
    """
    print(f"\n[RETRIEVAL] Query: '{query}'")
    
    target_intents = classify_query_intent(query)
    
    query_vec = generate_embeddings(query)
    if not query_vec: return []

    all_memories = get_all_memories(db)
    candidates = []
    
    for m in all_memories:
        # Governance/Conflict Filter: Ignore archived or superseded memories
        if m.archived or getattr(m, 'superseded', False): 
            continue
        
        if not m.embedding: 
            continue
        m_vec = json.loads(m.embedding)
        sim_score = cosine_similarity(query_vec, m_vec)
        
        metrics = compute_rerank_score(query, m, sim_score, target_intents)
        
        candidates.append({
            "memory": m,
            **metrics
        })

    candidates.sort(key=lambda x: x["final_score"], reverse=True)
    
    # Early pruning of weak candidates
    absolute_threshold = 0.58
    preliminary = [c for c in candidates[:limit] if c["final_score"] > absolute_threshold]
    
    if not preliminary:
        return []

    top_score = preliminary[0]["final_score"]
    relative_delta = 0.08 if top_score > 0.8 else 0.12
    
    final_memories = [
        c for c in preliminary 
        if c["final_score"] >= (top_score - relative_delta)
    ]

    for c in final_memories:
        m = c["memory"]
        f_score = c.get('final_score', 0.0)
        s_score = m.strength_score if m.strength_score is not None else 1.0
        m_label = getattr(m, 'key', None) or getattr(m, 'lesson', None) or getattr(m, 'summary', 'N/A')
        m_cat = getattr(m, 'category', 'fact') or 'fact'
        
        print(f"  - [{float(f_score):.3f}] Cat: {str(m_cat):<10} | Key: {str(m_label)[:20]:<20} | Strength: {float(s_score):.3f}")
        # Governance Reinforcement
        reinforce_memory(db, m)
        
    return [c["memory"] for c in final_memories]
