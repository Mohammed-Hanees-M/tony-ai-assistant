import json
import math
from sqlalchemy.orm import Session
from apps.backend.database.models.episode import EpisodicMemory
from apps.backend.llm.inference import generate_embeddings
from apps.backend.llm.memory_governance import reinforce_memory

# Re-use math helpers from memory_retriever if possible, but for modularity I'll include them.
def dot_product(v1, v2):
    return sum(x * y for x, y in zip(v1, v2))

def magnitude(v):
    return math.sqrt(sum(x * x for x in v))

def cosine_similarity(v1, v2):
    if not v1 or not v2: return 0.0
    m1, m2 = magnitude(v1), magnitude(v2)
    if m1 == 0 or m2 == 0: return 0.0
    return dot_product(v1, v2) / (m1 * m2)

def retrieve_relevant_episodes(db: Session, query: str, limit: int = 3):
    """
    Retrieves past experiences (episodes) relevant to the current query.
    """
    query_vec = generate_embeddings(query)
    if not query_vec: return []

    episodes = db.query(EpisodicMemory).filter(EpisodicMemory.archived == False).all()
    scored = []
    
    for ep in episodes:
        if not ep.embedding: continue
        try:
            ep_vec = json.loads(ep.embedding)
            score = cosine_similarity(query_vec, ep_vec)
            
            # Boost based on importance, strength, and confidence
            strength = getattr(ep, 'strength_score', 1.0) or 1.0
            confidence = getattr(ep, 'confidence_score', 1.0) or 1.0
            
            adjusted_score = score * (0.8 + 0.1 * strength + 0.1 * confidence)
            boosted_score = adjusted_score + (ep.importance * 0.05) 
            
            scored.append((boosted_score, ep))
        except: continue
        
    scored.sort(key=lambda x: x[0], reverse=True)
    
    # Threshold for experiences (often more distinct than facts)
    filtered = [ep for score, ep in scored if score > 0.5]
    final_episodes = filtered[:limit]
    
    if final_episodes:
        print(f"[DEBUG] Retrieved {len(final_episodes)} relevant past experiences.")
        for ep in final_episodes:
            reinforce_memory(db, ep)
        
    return final_episodes
