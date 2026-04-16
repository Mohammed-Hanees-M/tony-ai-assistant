import json
import re
from typing import List, Optional
from apps.backend.schemas.tool import ToolRoutingDecision, ToolExecutionTrace, ToolReflection
from apps.backend.llm.inference import run_llm_inference

_GLOBAL_TOOL_REFLECTIONS: List[ToolReflection] = []

REFLECTION_PROMPT = """
You are Tony's Post-Execution Tool Reflector.
Analyze the provided user query, routing plan, and execution trace to identify operational lessons.

If this is a major failure or a highly consistent success pattern, generate a structured lesson.
If this is minor noise or standard execution with nothing special to learn, return "NO_LESSON".

Output MUST be either "NO_LESSON" or pure JSON:
{
  "lesson": "Short actionable lesson",
  "context_pattern": "What type of query triggers this",
  "tool_pattern": "What tool interactions are involved",
  "success_case": true|false,
  "confidence": 0.5-1.0
}
"""

def extract_json(text: str) -> str:
    try:
        if "NO_LESSON" in text: return "NO_LESSON"
        match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
        if match: return match.group(1)
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1: return text[start:end+1]
        return text
    except: return text

def merge_reflection(new_reflection: ToolReflection) -> ToolReflection:
    # Basic similarity match for merging
    for existing in _GLOBAL_TOOL_REFLECTIONS:
        if existing.tool_pattern == new_reflection.tool_pattern and existing.success_case == new_reflection.success_case:
            print(f"[REFLECTOR] Merging duplicate lesson for {new_reflection.tool_pattern}")
            existing.confidence = min(1.0, existing.confidence + 0.2)
            existing.supporting_examples.extend(new_reflection.supporting_examples)
            if not existing.lesson.startswith("Reinforced:"):
                existing.lesson = f"Reinforced: {existing.lesson}"
            return existing
    
    _GLOBAL_TOOL_REFLECTIONS.append(new_reflection)
    print(f"[REFLECTOR] Saved new lesson for {new_reflection.tool_pattern}")
    return new_reflection

def get_persisted_reflections() -> List[ToolReflection]:
    return _GLOBAL_TOOL_REFLECTIONS

def reflect_on_execution(user_query: str, routing_decision: ToolRoutingDecision, execution_trace: ToolExecutionTrace, model: str = "phi3") -> Optional[ToolReflection]:
    print(f"\n[REFLECTOR] Analyzing trace for query: '{user_query[:30]}...'")
    
    if len(execution_trace.results) == 0:
        print("[REFLECTOR] No tools executed. Skipping reflection.")
        return None
        
    trace_dump = execution_trace.model_dump_json(indent=2)
    routing_dump = routing_decision.model_dump_json(indent=2)
    
    content = f"Query: {user_query}\nRouting:\n{routing_dump}\nTrace:\n{trace_dump}\n\nAnalyze and return NO_LESSON or JSON."
    
    messages = [
        {"role": "system", "content": REFLECTION_PROMPT},
        {"role": "user", "content": content}
    ]
    
    raw = run_llm_inference(messages, model)
    json_str = extract_json(raw)
    
    if json_str.strip() == "NO_LESSON":
        print("[REFLECTOR] Analysis complete: NO_LESSON (Filtered out noise)")
        return None
        
    try:
        data = json.loads(json_str)
        # Learning thresholds logic check
        confidence = float(data.get("confidence", 0.5))
        if confidence < 0.6 and not data.get("success_case", True):
            print(f"[REFLECTOR] Rejecting low-confidence failure (Noise Filtering). Confidence: {confidence}")
            return None
            
        reflection = ToolReflection(
            lesson=data.get("lesson", "Unknown lesson"),
            context_pattern=data.get("context_pattern", "Unknown context"),
            tool_pattern=data.get("tool_pattern", "Unknown tool"),
            success_case=bool(data.get("success_case", True)),
            confidence=confidence,
            supporting_examples=[user_query]
        )
        
        merged = merge_reflection(reflection)
        return merged
        
    except Exception as e:
        print(f"[REFLECTOR] Failed to parse reflection JSON: {e}")
        return None
