import json
import re
from typing import Dict, Any
from apps.backend.schemas.tool import ToolRoutingDecision, ToolSelection
from apps.backend.llm.inference import run_llm_inference
from apps.backend.tools.registry import get_registry_manifest, is_tool_registered
from apps.backend.utils.json_parser import safe_parse_json

TOOL_ROUTING_PROMPT = """
You are Tony's Tool Reasoning Engine. Determine if the user's query requires external tools to properly execute.
If so, select the best tools from the provided registry.

AVAILABLE TOOLS:
{registry_manifest}

Output ONLY valid JSON structured as follows:
{{
  "requires_tools": true|false,
  "selections": [
    {{
      "tool_name": "exact_tool_name_from_registry",
      "confidence": 0.95,
      "reason": "Why this tool is chosen",
      "required_inputs": {{"param1": "value"}}
    }}
  ],
  "fallback_strategy": "What to do if tools fail",
  "reasoning_summary": "Overall reasoning for tool choices"
}}

RULES:
1. If no tools are needed, set "requires_tools": false and leave "selections" empty.
2. DO NOT hallucinate tools. Only use tools from AVAILABLE TOOLS.
3. Output strictly JSON. No markdown wrappers.
"""

def parse_and_validate_routing(raw_output: str) -> ToolRoutingDecision:
    try:
        data = safe_parse_json(raw_output, fallback={})
        if not data:
             raise ValueError("No valid JSON found")
        
        selections = []
        for s in data.get("selections", []):
            tool_name = s.get("tool_name")
            if not is_tool_registered(tool_name):
                print(f"[TOOL ROUTER] Validator rejected unknown tool: {tool_name}")
                continue
            
            selections.append(ToolSelection(
                tool_name=tool_name,
                confidence=float(s.get("confidence", 1.0)),
                reason=s.get("reason", ""),
                required_inputs=s.get("required_inputs", {})
            ))
            
        decision = ToolRoutingDecision(
            requires_tools=bool(data.get("requires_tools", False)) and len(selections) > 0,
            selections=selections,
            fallback_strategy=data.get("fallback_strategy", ""),
            reasoning_summary=data.get("reasoning_summary", "")
        )
        print(f"[TOOL ROUTER] Parsed correctly. Requires tools: {decision.requires_tools}. Valid tools: {len(decision.selections)}")
        return decision
        
    except Exception as e:
        print(f"[TOOL ROUTER] Validation failed on malformed output: {e}. Generating safe fallback.")
        return ToolRoutingDecision(
            requires_tools=False,
            selections=[],
            fallback_strategy="Reply using general knowledge base.",
            reasoning_summary="System encountered a parsing error and fell back to no-tool mode."
        )

def route_tools_for_task(user_query: str, context: dict, model: str = "phi3") -> ToolRoutingDecision:
    print(f"\n[TOOL ROUTER] Evaluating task for tool usage: '{user_query}'")
    
    registry_str = get_registry_manifest()
    sys_prompt = TOOL_ROUTING_PROMPT.format(registry_manifest=registry_str)
    
    context_str = json.dumps(context, default=str)
    
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": f"Context: {context_str}\n\nTask: {user_query}"}
    ]
    
    raw_response = run_llm_inference(messages, model)
    print(f"[TOOL ROUTER] Raw output received. Length: {len(raw_response)}")
    
    decision = parse_and_validate_routing(raw_response)
    
    if decision.requires_tools:
        for s in decision.selections:
            print(f"  -> Tool Selected: {s.tool_name} (conf: {s.confidence:.2f})")
    else:
        print("  -> Tool Selected: None")
        
    return decision
