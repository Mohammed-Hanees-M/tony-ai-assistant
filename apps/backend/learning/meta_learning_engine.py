import json
import re
from typing import List
from apps.backend.schemas.learning import PerformanceMetric, ImprovementProposal
from apps.backend.llm.inference import run_llm_inference

META_LEARNING_PROMPT = """You are Tony's Meta-Learning AI. Analyze the performance metrics of the given subsystems.
Identify recurring failures, degraded success rates, abnormal latency, or high fallback rates.
Only generate proposals for systems that are genuinely unhealthy or explicitly degraded. DO NOT generate proposals for perfectly healthy systems.

Generate a JSON list of proposals structured EXACTLY like this:
[
  {
    "title": "Fix World Model Timeout",
    "affected_subsystem": "world_model",
    "observed_problem": "High fallback rate of 0.8",
    "hypothesis": "The LLM parsing logic is failing consistently on complex outputs.",
    "suggested_fix": "Rewrite regex to handle scattered markdown tags.",
    "confidence": 0.9,
    "risk_level": "medium"
  }
]
"""

def extract_json_list(raw_text: str) -> List[dict]:
    try:
        match = re.search(r'\[\s*\{.*?\}\s*\]', raw_text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return []
    except Exception:
        return []

def analyze_system_performance(metrics: List[PerformanceMetric]) -> List[PerformanceMetric]:
    print(f"[META LEARNING] Analyzing {len(metrics)} subsystems...")
    problematic = []
    for m in metrics:
        unhealthy = False
        if m.success_rate < 0.8: unhealthy = True
        if m.fallback_rate > 0.3: unhealthy = True
        if m.error_count > 5: unhealthy = True
        
        if unhealthy:
            print(f"[META LEARNING] Detected anomaly pattern in: {m.subsystem_name}")
            problematic.append(m)
    
    if not problematic:
        print("[META LEARNING] All systems healthy. No architectural optimizations required.")
        
    return problematic

def generate_improvement_proposals(metrics: List[PerformanceMetric], model: str = "phi3") -> List[ImprovementProposal]:
    problematic = analyze_system_performance(metrics)
    if not problematic:
        return []
        
    print(f"[META LEARNING] Generating proposals for {len(problematic)} subsystems...")
    metrics_dump = [m.model_dump() for m in problematic]
    
    messages = [
        {"role": "system", "content": META_LEARNING_PROMPT},
        {"role": "user", "content": f"Problematic Subsystem Data:\n{json.dumps(metrics_dump, indent=2)}"}
    ]
    
    raw = run_llm_inference(messages, model)
    parsed = extract_json_list(raw)
    
    proposals = []
    for p in parsed:
        try:
            proposals.append(ImprovementProposal(
                title=p.get("title", "Unknown Optimization"),
                affected_subsystem=p.get("affected_subsystem", "unknown"),
                observed_problem=p.get("observed_problem", ""),
                hypothesis=p.get("hypothesis", ""),
                suggested_fix=p.get("suggested_fix", ""),
                confidence=float(p.get("confidence", 0.5)),
                risk_level=p.get("risk_level", "high")
            ))
        except Exception as e:
            print(f"[META LEARNING] Schema enforcement error parsing proposal: {e}")
            
    return proposals

def rank_improvement_opportunities(proposals: List[ImprovementProposal]) -> List[ImprovementProposal]:
    if not proposals:
        return []
    print("[META LEARNING] Ranking improvement opportunities by impact and risk...")
    risk_weights = {"low": 1, "medium": 2, "high": 3}
    
    return sorted(proposals, key=lambda x: (-x.confidence, risk_weights.get(x.risk_level.lower(), 3)))

def run_meta_learning_cycle(metrics: List[PerformanceMetric], model: str = "phi3") -> List[ImprovementProposal]:
    proposals = generate_improvement_proposals(metrics, model)
    return rank_improvement_opportunities(proposals)
