from typing import Dict, Any
from apps.backend.agents.delegation_router import select_specialists_for_task
from apps.backend.agents.specialist_registry import get_specialist
from apps.backend.agents.parallel_executor import execute_specialists_parallel
from apps.backend.agents.debate_engine import run_specialist_debate
from apps.backend.llm.inference import run_llm_inference

def run_multi_agent_workflow(query: str, model: str = "phi3") -> Dict[str, Any]:
    print(f"\n[MULTI-AGENT ORCHESTRATOR] Initializing workflow for: '{query}'")
    
    # 1. Select specialists
    selections = select_specialists_for_task(query, model)
    
    # 2. Delegate subtasks parallelly
    results = execute_specialists_parallel(selections, query, model)
    
    # 3. Cross-Verification / Debate
    debate_res = run_specialist_debate(results, query, model)
    
    # 4. Aggregate / Synthesize final result
    if not results:
        return {"final_output": "Failed to generate any specialist output.", "specialist_results": []}
        
    print(f"[MULTI-AGENT ORCHESTRATOR] Aggregating {len(results)} specialist outputs...")
    
    agg_prompt = "You are the Coordinator. Synthesize the findings from your specialist sub-agents into a final cohesive response to the user's original query."
    
    context_str = ""
    for r in results:
        context_str += f"\n--- {r.specialist_id.upper()} ---\n{r.output}\n"
        
    debate_context = ""
    if debate_res.conflict_detected:
        debate_context = f"\n\n--- DEBATE RESOLUTION ---\nSummary: {debate_res.resolution_summary}\nWinning Position: {debate_res.winning_position}\n"
        
    messages = [
        {"role": "system", "content": agg_prompt},
        {"role": "user", "content": f"Query: {query}\n\nSpecialist Findings:{context_str}{debate_context}"}
    ]
    
    final_output = run_llm_inference(messages, model)
    
    print("[MULTI-AGENT ORCHESTRATOR] Workflow complete.")
    return {
        "final_output": final_output.strip(),
        "specialist_results": [r.model_dump() for r in results],
        "debate_result": debate_res.model_dump()
    }
