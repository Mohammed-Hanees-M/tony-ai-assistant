from apps.backend.schemas.agent import SpecialistProfile, SpecialistResult
from apps.backend.llm.inference import run_llm_inference

def execute_specialist_task(specialist: SpecialistProfile, subtask: str, model: str = "phi3") -> SpecialistResult:
    print(f"[SUB-AGENT EXECUTOR] Dispatching to '{specialist.name}'...")
    
    sys_prompt = f"""You are Tony's {specialist.name}.
Domain: {specialist.domain}
Tags: {', '.join(specialist.capability_tags)}

Perform this subtask to the best of your ability. Keep it concise.
"""
    
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": subtask}
    ]
    
    raw_output = run_llm_inference(messages, model)
    
    # Simulated confidence metric hook for future validation layers
    confidence = 0.9 if len(raw_output) > 20 else 0.5
    
    result = SpecialistResult(
        specialist_id=specialist.id,
        subtask=subtask,
        output=raw_output.strip(),
        confidence=confidence,
        metadata={"model_used": model}
    )
    
    print(f"[SUB-AGENT EXECUTOR] '{specialist.name}' finished (Confidence: {confidence}).")
    return result
