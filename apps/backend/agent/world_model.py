import json
import re
from typing import List
from apps.backend.schemas.simulation import SimulationResult
from apps.backend.schemas.plan import Plan
from apps.backend.llm.inference import run_llm_inference

SIMULATION_PROMPT = """You are Tony's Internal World Model Simulator.
Analyze the following candidate plan/action within the given context.
Predict the likely outcome, success probability, latency logic, potential side-effects, and failure modes.

Return a JSON object:
{
  "success_probability": 0.85, 
  "risk_score": 0.2,            
  "estimated_latency": 1500,    
  "estimated_cost": 0.05,       
  "predicted_side_effects": ["file changed", "network request sent"],
  "predicted_failure_modes": ["timeout", "permission denied"],
  "recommendation_score": 0.75  
}
"""

def simulate_candidate_action(candidate_id: str, description: str, context: dict, model: str = "phi3") -> SimulationResult:
    print(f"[WORLD MODEL] Simulating '{candidate_id}'...")
    
    messages = [
        {"role": "system", "content": SIMULATION_PROMPT},
        {"role": "user", "content": f"Context: {json.dumps(context)}\n\nCandidate Action: {description}"}
    ]
    
    raw = run_llm_inference(messages, model)
    
    try:
        match = re.search(r'\{.*?\}', raw, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
        else:
            raise ValueError("No JSON found")
    except:
        print("[WORLD MODEL] Malformed simulation JSON. Falling back to safe heuristics.")
        data = {
            "success_probability": 0.1, "risk_score": 0.9, "estimated_latency": 1000.0,
            "estimated_cost": 0.0, "predicted_side_effects": ["Unknown Context"],
            "predicted_failure_modes": ["LLM Parsing Fault"], "recommendation_score": 0.1
        }
        
    res = SimulationResult(
        candidate_id=candidate_id,
        description=description,
        success_probability=float(data.get("success_probability", 0.1)),
        risk_score=float(data.get("risk_score", 0.9)),
        estimated_latency=float(data.get("estimated_latency", 1000.0)),
        estimated_cost=float(data.get("estimated_cost", 0.0)),
        predicted_side_effects=data.get("predicted_side_effects", []),
        predicted_failure_modes=data.get("predicted_failure_modes", []),
        recommendation_score=float(data.get("recommendation_score", 0.1))
    )
    print(f"[WORLD MODEL] Simulation complete: Score={res.recommendation_score}, Risk={res.risk_score}")
    return res

def compare_candidate_plans(plans: List[Plan], context: dict, model: str = "phi3") -> List[SimulationResult]:
    results = []
    for i, plan in enumerate(plans):
        desc = f"Plan {i}: {plan.title} - Steps: {[s.description for s in plan.steps]}"
        sim_res = simulate_candidate_action(plan.id, desc, context, model)
        results.append(sim_res)
        
    # Sort by recommendation_score descending, then inversely by risk_score
    results.sort(key=lambda x: (x.recommendation_score, -x.risk_score), reverse=True)
    return results
