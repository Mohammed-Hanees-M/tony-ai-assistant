import json
import re
from typing import List, Optional
from apps.backend.schemas.agent import SpecialistResult, DebateResult, Critique
from apps.backend.llm.inference import run_llm_inference

CONFLICT_DETECT_PROMPT = """You are the Conflict Detector. Read the query and the specialist responses.
Determine if there are factual contradictions, major conflicting recommendations, or severe semantic disagreements between the responses.
Return a JSON object:
{
  "conflict_detected": true,
  "reason": "Brief reason if true",
  "conflicting_specialists": ["id1", "id2"]
}
"""

CRITIQUE_PROMPT = """You are the {critiquer} specialist. You disagree with {target}.
Review their output: "{target_output}"
Provide a brief critique and a proposed resolution.
"""

ARBITRATOR_PROMPT = """You are the Arbitrator. Review the query, original outputs, and the critiques.
Decide the resolution.
Return a JSON object:
{
  "resolution_summary": "Brief summary",
  "winning_position": "id1 or id2 or 'compromise'",
  "confidence_adjustment": 0.1
}
"""

def extract_json_mapping(raw: str):
    try:
        match = re.search(r'\{.*?\}', raw, re.DOTALL)
        if match: return json.loads(match.group(0))
    except:
        pass
    return {}

def detect_conflict(results: List[SpecialistResult], query: str, model: str) -> dict:
    if len(results) < 2:
        return {"conflict_detected": False}
        
    context = "\n".join([f"{r.specialist_id}: {r.output}" for r in results])
    messages = [
        {"role": "system", "content": CONFLICT_DETECT_PROMPT},
        {"role": "user", "content": f"Query: {query}\n\nResponses:\n{context}"}
    ]
    raw = run_llm_inference(messages, model)
    return extract_json_mapping(raw)

def run_specialist_debate(specialist_results: List[SpecialistResult], query: str, model: str = "phi3") -> DebateResult:
    # 1. Detect conflict
    detection = detect_conflict(specialist_results, query, model)
    if not detection.get("conflict_detected", False):
        print("[DEBATE ENGINE] No significant conflicts detected. Skipping debate.")
        return DebateResult(conflict_detected=False)
        
    conflicting_ids = detection.get("conflicting_specialists", [])
    print(f"[DEBATE ENGINE] Conflict detected between {conflicting_ids}. Reason: {detection.get('reason')}")
    
    # Isolate targets
    participants = [r for r in specialist_results if r.specialist_id in conflicting_ids]
    if len(participants) < 2:
        participants = specialist_results[:2] # Fallback if IDs didn't match cleanly
        
    critiques = []
    
    # 2. Generate critiques
    for i in range(len(participants)):
        for j in range(len(participants)):
            if i != j:
                critiquer = participants[i]
                target = participants[j]
                print(f"[DEBATE ENGINE] '{critiquer.specialist_id}' is critiquing '{target.specialist_id}'...")
                
                messages = [
                    {"role": "system", "content": CRITIQUE_PROMPT.format(
                        critiquer=critiquer.specialist_id, target=target.specialist_id, target_output=target.output
                    )},
                    {"role": "user", "content": f"Original query was: {query}. What is your critique?"}
                ]
                critique_raw = run_llm_inference(messages, model)
                critiques.append(Critique(
                    critiquer_id=critiquer.specialist_id,
                    target_id=target.specialist_id,
                    critique_text=critique_raw.strip(),
                    proposed_resolution="Refer to critique text."
                ))
                
    # 3. Arbitration
    print("[DEBATE ENGINE] Arbitrating resolution...")
    critique_context = "\n".join([f"{c.critiquer_id} says: {c.critique_text}" for c in critiques])
    arb_messages = [
        {"role": "system", "content": ARBITRATOR_PROMPT},
        {"role": "user", "content": f"Query: {query}\n\nCritiques:\n{critique_context}"}
    ]
    arb_raw = run_llm_inference(arb_messages, model)
    arb_data = extract_json_mapping(arb_raw)
    
    resolution = arb_data.get("resolution_summary", "Resolved via compromise.")
    winner = arb_data.get("winning_position", "compromise")
    conf_adj = arb_data.get("confidence_adjustment", 0.0)
    
    print(f"[DEBATE ENGINE] Resolution: {resolution} (Winner: {winner}) (Conf_Adj: {conf_adj})")
    
    return DebateResult(
        conflict_detected=True,
        participants=[p.specialist_id for p in participants],
        critiques=critiques,
        resolution_summary=resolution,
        winning_position=winner,
        confidence_adjustment=float(conf_adj)
    )
