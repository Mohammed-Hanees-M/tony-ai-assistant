import re
import json
from typing import Optional
from sqlalchemy.orm import Session
from apps.backend.llm.inference import run_llm_inference, generate_embeddings
from apps.backend.database.models.reflection import ReflectiveMemory
from apps.backend.llm.router import route_model

REFLECTION_PROMPT = """You are Tony's meta-cognition engine. Analyze the recent conversation turn.
Your goal is to identify NEWly learned lessons, strategy shifts, or workflow preferences.

CRITICAL RULES:
1. NO SELF-REINFORCEMENT: Ignore the AI's compliance with existing rules. If the AI is just FOLLOWING a known preference (e.g., using Python because the user previously asked), do NOT extract a reflection.
2. NEW EVIDENCE ONLY: Only extract a lesson if the USER provides a NEW explicit requirement, a NEW preference, or an EXPLICIT correction/praise for the AI's strategy.
3. GROUNDING: Bounded strictly by the USER'S direct input and the outcome. 
4. If the turn is just routine execution of already established patterns, return 'NONE'.

Output JSON if a GENUINE NEW lesson is found, else 'NONE'.
{
  "lesson": "Generalized statement of the NEW lesson",
  "context": "Focus area (e.g., coding, project_logic, workflow)",
  "importance": 1-5,
  "is_success": true
}
"""

def extract_reflection(user_msg: str, ai_msg: str) -> Optional[dict]:
    """Analyzes a turn to see if a meta-lesson was learned."""
    if len(user_msg) < 20: return None

    prompt = [
        {"role": "system", "content": REFLECTION_PROMPT},
        {"role": "user", "content": f"USER: {user_msg}\nAI: {ai_msg}"}
    ]

    model = route_model(user_msg, purpose="extraction")
    response = run_llm_inference(prompt, model)
    print(f"[DEBUG] Reflector Raw Response: {response}")
    if "NONE" in response.upper() or "{" not in response:
        return None

    try:
        match = re.search(r"(\{.*\})", response, re.DOTALL)
        if not match: 
            print("[DEBUG] No JSON block found in Reflector response.")
            return None
        data = json.loads(match.group(1))
        print(f"[DEBUG] Extracted Reflection Data: {data}")
        return data
    except Exception as e:
        print(f"[DEBUG] Reflection parsing error: {e}")
        return None

def upsert_reflection(db: Session, lesson_data: dict):
    """Saves or updates a reflection based on similarity."""
    lesson_text = lesson_data["lesson"]
    query_vec = generate_embeddings(lesson_text)
    
    # Check for similar existing reflections
    reflections = db.query(ReflectiveMemory).all()
    existing = None
    
    # Simple semantic similarity check for deduplication
    for r in reflections:
        if not r.embedding: continue
        r_vec = json.loads(r.embedding)
        # Re-use cosine if possible, but for brevity I'll check exact context or use a shim
        from apps.backend.llm.episodic_retriever import cosine_similarity
        if cosine_similarity(query_vec, r_vec) > 0.85:
            existing = r
            break
            
    if existing:
        print(f"[DEBUG] Updating existing reflection: {existing.lesson}")
        if lesson_data.get("is_success", True):
            existing.success_count += 1
            existing.confidence = min(1.0, existing.confidence + 0.1)
        else:
            existing.failure_count += 1
            existing.confidence = max(0.0, existing.confidence - 0.1)
        existing.importance = max(existing.importance, lesson_data["importance"])
    else:
        print(f"[DEBUG] Creating NEW reflection: {lesson_text}")
        new_ref = ReflectiveMemory(
            lesson=lesson_text,
            context=lesson_data["context"],
            importance=lesson_data["importance"],
            confidence=0.6,
            success_count=1 if lesson_data.get("is_success", True) else 0,
            failure_count=0 if lesson_data.get("is_success", True) else 1,
            embedding=json.dumps(query_vec) if query_vec else None
        )
        db.add(new_ref)
        
    db.commit()
