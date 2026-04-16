import json
import uuid
import re
from typing import List, Optional, Dict
from apps.backend.schemas.strategy import WorkflowStrategyProfile
from apps.backend.schemas.tool import ToolExecutionTrace
from apps.backend.llm.inference import run_llm_inference

_GLOBAL_STRATEGY_PROFILES: Dict[str, List[WorkflowStrategyProfile]] = {}

STRATEGY_PROMPT = """
You are Tony's Workflow Strategy Optimizer. Analyze the provided user query and tool execution trace.
Determine the high-level context of this task and the structural workflow pattern that was executed.

Output strictly as JSON:
{
  "context_pattern": "What type of problem the user is solving (e.g., Data Analysis, Web Research)",
  "workflow_pattern": "The abstract sequence of tools used (e.g., document_reader -> python_interpreter)",
  "notes": "Short summary of the strategy"
}
"""

def extract_json(raw_text: str) -> str:
    try:
        match = re.search(r'```(?:json)?\s*(.*?)\s*```', raw_text, re.DOTALL)
        if match: return match.group(1)
        start = raw_text.find('{')
        end = raw_text.rfind('}')
        if start != -1 and end != -1: return raw_text[start:end+1]
        return raw_text
    except: return raw_text

def update_profile_metrics(profile: WorkflowStrategyProfile, success: bool, latency: float):
    # Rolling average calculation
    total_latency = (profile.avg_latency_ms * profile.usage_count) + latency
    total_success = (profile.success_rate * profile.usage_count) + (1.0 if success else 0.0)
    
    profile.usage_count += 1
    profile.avg_latency_ms = total_latency / profile.usage_count
    profile.success_rate = total_success / profile.usage_count
    
    # Confidence scales with usage count
    profile.confidence = min(1.0, profile.usage_count * 0.25)
    
def rank_and_update_preferred(context_pattern: str):
    profiles = _GLOBAL_STRATEGY_PROFILES.get(context_pattern, [])
    if not profiles: return
    
    # Reset preferred
    for p in profiles: p.preferred = False
    
    # Sort criteria: Success Rate (desc), Latency (asc), Confidence (desc)
    # Only consider profiles with usage_count >= 2 (Noise filtering)
    valid_profiles = [p for p in profiles if p.usage_count >= 2]
    
    if not valid_profiles:
        print(f"[STRATEGY] No profiles for '{context_pattern}' meet minimum usage threshold (2).")
        return
        
    valid_profiles.sort(key=lambda p: (p.success_rate, -p.avg_latency_ms, p.confidence), reverse=True)
    
    preferred = valid_profiles[0]
    preferred.preferred = True
    print(f"[STRATEGY] Ranking updated for '{context_pattern}'. New preferred strategy: {preferred.workflow_pattern} (Success: {preferred.success_rate*100:.1f}%, Latency: {preferred.avg_latency_ms:.1f}ms)")
    
def analyze_and_optimize_strategy(user_query: str, execution_trace: ToolExecutionTrace, execution_success: bool, model: str = "phi3") -> Optional[WorkflowStrategyProfile]:
    if not execution_trace.results:
        return None
        
    trace_dump = execution_trace.model_dump_json()
    total_latency = sum(r.execution_time_ms for r in execution_trace.results)
    
    messages = [
        {"role": "system", "content": STRATEGY_PROMPT},
        {"role": "user", "content": f"Query: {user_query}\nTrace: {trace_dump}"}
    ]
    
    raw = run_llm_inference(messages, model)
    json_str = extract_json(raw)
    
    try:
        data = json.loads(json_str)
        context_pattern = data.get("context_pattern", "Unknown")
        workflow_pattern = data.get("workflow_pattern", "Unknown")
        notes = data.get("notes", "")
        
        if context_pattern not in _GLOBAL_STRATEGY_PROFILES:
            _GLOBAL_STRATEGY_PROFILES[context_pattern] = []
            
        profiles = _GLOBAL_STRATEGY_PROFILES[context_pattern]
        
        # Find existing profile
        profile = next((p for p in profiles if p.workflow_pattern == workflow_pattern), None)
        
        if not profile:
            profile = WorkflowStrategyProfile(
                id=str(uuid.uuid4()),
                context_pattern=context_pattern,
                workflow_pattern=workflow_pattern,
                notes=notes
            )
            profiles.append(profile)
            print(f"[STRATEGY] Created new profile: {workflow_pattern} for context '{context_pattern}'")
            
        update_profile_metrics(profile, execution_success, total_latency)
        
        print(f"[STRATEGY] Updated metrics - Usage: {profile.usage_count}, Success: {profile.success_rate:.2f}, Latency: {profile.avg_latency_ms:.2f}ms")
        
        rank_and_update_preferred(context_pattern)
        
        return profile
    except Exception as e:
        print(f"[STRATEGY] Failed to parse analysis: {e}")
        return None

def get_preferred_strategy(context_query: str) -> Optional[WorkflowStrategyProfile]:
    # Simulate semantic match for now
    for context, profiles in _GLOBAL_STRATEGY_PROFILES.items():
        if context_query.lower() in context.lower() or context.lower() in context_query.lower():
            for p in profiles:
                if p.preferred: return p
    return None
