import json
from sqlalchemy.orm import Session
from apps.backend.database.models.reflection import ReflectiveMemory
from apps.backend.llm.inference import generate_embeddings
from apps.backend.llm.episodic_retriever import cosine_similarity
from apps.backend.llm.memory_governance import reinforce_memory

def retrieve_relevant_reflections(db: Session, query: str, limit: int = 3):
    """Retrieves learned lessons relevant to the current query."""
    query_vec = generate_embeddings(query)
    if not query_vec: return []

    reflections = db.query(ReflectiveMemory).filter(ReflectiveMemory.archived == False).all()
    scored = []
    
    for r in reflections:
        if not r.embedding: continue
        try:
            r_vec = json.loads(r.embedding)
            score = cosine_similarity(query_vec, r_vec)
            
            # Boost by importance and confidence
            rs_score = r.strength_score if r.strength_score is not None else 1.0
            conf_score = getattr(r, 'confidence_score', 1.0)
            if conf_score is None: conf_score = 1.0
            
            final_score = score * (0.8 + 0.1 * rs_score + 0.1 * conf_score) + (getattr(r, 'importance', 1) * 0.05)
            print(f"[DEBUG] Reflection Score: {final_score:.4f} | Similarity: {score:.4f} | Context: {r.context} | Strength: {rs_score:.3f} | Confidence: {conf_score:.3f}")
            
            scored.append((final_score, r))
        except: continue
        
    scored.sort(key=lambda x: x[0], reverse=True)
    
    # Filter by threshold (Lowered to 0.35 for broader strategy recall)
    filtered = [r for score, r in scored if score > 0.35]
    final_reflections = filtered[:limit]
    
    if final_reflections:
        print(f"[DEBUG] Retrieved {len(final_reflections)} relevant reflections/lessons.")
        for r in final_reflections:
            reinforce_memory(db, r)
        
    return final_reflections
