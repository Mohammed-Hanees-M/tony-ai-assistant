import json
import uuid
import re
from typing import Dict, Any, Tuple
from apps.backend.schemas.reasoning import ReasoningTrace, ReasoningStep
from apps.backend.llm.inference import run_llm_inference
from apps.backend.llm.router import route_model
from apps.backend.utils.json_parser import safe_parse_json

REASONING_PROMPT = """
You are Tony's Multi-Step Reasoning Engine. Before answering a complex query, you must think step-by-step.

TONY PERSONA ALIGNMENT (MANDATORY):
- You are Tony, built and owned by Mohammed Hanees Mullakkal.
- NEVER claim to be created by Microsoft, OpenAI, or any other entity.
- NEVER mention your training data cutoff or knowledge limits unless explicitly asked.
- GROUND everything in the provided context.

Break down your reasoning into structured steps. Follow the structured JSON schema below strictly.

Output strictly as JSON:
{
  "steps": [
    {
      "order_index": 1,
      "thought": "State your initial thought or hypothesis.",
      "rationale": "Explain why you are thinking this.",
      "intermediate_result": "Any conclusion drawn from this specific step."
    }
  ],
  "final_conclusion": "Provide the final answer to the user.",
  "confidence": 0.95
}

Do NOT wrap your response in markdown code blocks, just pure raw JSON.
"""

def extract_json_safe(raw_text: str) -> dict:
    """Wrapper to use hardened safe_parse_json."""
    return safe_parse_json(raw_text, fallback={})

def ensure_string(val: Any) -> str:
    """Recursively attempts to extract a string if LLM returned a nested object."""
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        # Look for common content keys
        for key in ["message", "content", "answer", "text", "conclusion"]:
            if key in val:
                return str(val[key])
        # Join values if no key found
        return " ".join(str(v) for v in val.values())
    if isinstance(val, list):
        return " ".join(ensure_string(item) for item in val)
    return str(val)

def parse_and_validate_trace(raw_output: str, user_query: str, model: str = "phi3") -> ReasoningTrace:
    try:
        # Pre-process: Isolate JSON block
        match = re.search(r'```json\s*(.*?)\s*```', raw_output, re.DOTALL) or \
                re.search(r'\{(?:.|\n)*\}', raw_output, re.DOTALL)
        target = match.group(0) if match else raw_output
        data = extract_json_safe(target)
        
        if not data or "final_conclusion" not in data:
             # If it's not JSON, maybe it's just raw text?
             if "{" not in raw_output:
                 return ReasoningTrace(
                     query=user_query,
                     steps=[],
                     final_conclusion=raw_output,
                     confidence=0.8
                 )
             raise ValueError("Malformed JSON trace structure")

        trace_id = str(uuid.uuid4())
        steps = []
        for s_idx, s_data in enumerate(data.get("steps", [])):
            if not isinstance(s_data, dict): continue
            steps.append(ReasoningStep(
                id=f"step_{trace_id}_{s_idx}",
                thought=ensure_string(s_data.get("thought", "")),
                rationale=ensure_string(s_data.get("rationale", "")),
                intermediate_result=ensure_string(s_data.get("intermediate_result", "")),
                order_index=s_data.get("order_index", s_idx + 1)
            ))
            
        trace = ReasoningTrace(
            id=trace_id,
            query=user_query,
            steps=steps,
            final_conclusion=ensure_string(data.get("final_conclusion", "")),
            confidence=float(data.get("confidence", 1.0))
        )
        return trace
        
    except Exception as e:
        print(f"[REASONER] Critical parse failure ({e}). Running direct fallback.")
        # FINAL FALLBACK: Generate a direct response without structured output requirement
        fallback_msg = [
            {"role": "system", "content": "You are Tony. Provide a direct, natural response to the query. No JSON."},
            {"role": "user", "content": user_query}
        ]
        direct_response = run_llm_inference(fallback_msg, model)
        
        return ReasoningTrace(
            query=user_query,
            steps=[ReasoningStep(order_index=1, thought="Fallback", rationale="Reparsed via direct inference", intermediate_result=None)],
            final_conclusion=direct_response,
            confidence=0.5
        )

def generate_reasoned_response(user_query: str, context: Dict[str, Any], model: str = "phi3") -> Tuple[str, ReasoningTrace]:
    """Generates a reasoned response and returns (final_conclusion, trace)."""
    
    context_str = json.dumps(context, default=str)
    
    print(f"\n[REASONER] Generating reasoning trace for query: '{user_query}'")
    
    messages = [
        {"role": "system", "content": REASONING_PROMPT + f"\n\nContext:\n{context_str}"},
        {"role": "user", "content": user_query}
    ]
    
    model = route_model(user_query, purpose="reasoning")
    raw_response = run_llm_inference(messages, model)
    print(f"[REASONER] Raw output received. Length: {len(raw_response)}")
    
    trace = parse_and_validate_trace(raw_response, user_query, model=model)
    
    return trace.final_conclusion, trace

def generate_direct_response(user_query: str, context: Dict[str, Any], model: str = "phi3") -> str:
    """Fast-path synthesis: No JSON, no multi-step reasoning, just direct answering."""
    print(f"[REASONER] Generating direct synthesis (Fast-Path) for query: '{user_query[:50]}'")
    
    is_voice = context.get("interface") == "voice" or context.get("mode") == "production_fixed"
    voice_guidelines = ""
    if is_voice:
        voice_guidelines = """ 
        VOICE MODE ACTIVE:
        - Be extremely concise. Respond in 1-2 short sentences max.
        - ALWAYS use contractions (don't, it's, I'll, can't) for natural speech.
        - NEVER use markdown, lists, or robotic preambles.
        """

    context_str = ""
    # Extract pertinent context to keep prompt small
    for k, v in context.items():
         if "context" in k:
              context_str += f"\nRelevant Information:\n{v}\n"

    messages = [
        {"role": "system", "content": f"""
        You are Tony, a sophisticated AI assistant built and owned by Mohammed Hanees Mullakkal. 
        - NEVER claim affiliation with Microsoft or OpenAI.
        - NEVER mention training knowledge cutoffs.
        {voice_guidelines} 
        - TONY'S KNOWLEDGE: You have access to vast internal knowledge. 
        - If the query is about a general topic (science, math, history, definitions like "Quantum Mechanics"), PROVIDE A DETAILED ANSWER even if the "Relevant Information" section is empty.
        - ONLY say "I don't have enough information" if the query is about a specific personal fact or project-specific data that is missing from the context.
        - NEVER repeat technical headers like "GRAPH KNOWLEDGE MATRIX".
        - Answer directly and concisely.
        """},
        {"role": "user", "content": f"{context_str}\n\nQuery: {user_query}"}
    ]
    
    model = route_model(user_query, purpose="chat")
    return run_llm_inference(messages, model).strip()
