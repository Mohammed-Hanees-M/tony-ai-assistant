import json
import re
from typing import List
from apps.backend.schemas.agent import SpecialistProfile
from apps.backend.agents.specialist_registry import list_all_specialists
from apps.backend.llm.inference import run_llm_inference
from apps.backend.utils.json_parser import safe_parse_json

ROUTER_PROMPT = """
You are Tony's Delegation Router. Analyze the user's query and the list of available specialists.
Decide which specialists are required to fully complete the task.

Return a JSON list of objects containing:
[
  {
    "specialist_id": "id_of_specialist",
    "reason": "Why this specialist is needed",
    "priority": 1
  }
]
If the task is unknown or general, return an empty list.
"""

def select_specialists_for_task(query: str, model: str = "phi3") -> List[dict]:
    specialists = list_all_specialists()
    specs_json = json.dumps([s.model_dump() for s in specialists], indent=2)
    
    messages = [
        {"role": "system", "content": ROUTER_PROMPT},
        {"role": "user", "content": f"Query: {query}\n\nAvailable Specialists:\n{specs_json}"}
    ]
    
    raw = run_llm_inference(messages, model)
    selection = safe_parse_json(raw, fallback=[])
    
    if not isinstance(selection, list):
        selection = []
    
    # Sort by priority
    selection.sort(key=lambda x: int(x.get("priority", 99)))
    
    if not selection:
        print("[DELEGATION] Unknown task or LLM failure. Falling back to writing_expert safely.")
        return [{"specialist_id": "writing_expert", "reason": "Fallback default evaluator", "priority": 99}]
        
    for s in selection:
        print(f"[DELEGATION] Selected {s.get('specialist_id')} (Priority: {s.get('priority')}) - {s.get('reason')}")
        
    return selection
