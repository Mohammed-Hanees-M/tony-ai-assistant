import time
from typing import Any, Dict
from apps.backend.schemas.tool import ToolRoutingDecision, ToolExecutionResult, ToolExecutionTrace
from apps.backend.tools.registry import AVAILABLE_TOOLS
import inspect

def validate_inputs(tool_name: str, inputs: Dict[str, Any]) -> bool:
    tool_meta = AVAILABLE_TOOLS.get(tool_name)
    if not tool_meta:
        return False
    required_params = tool_meta.get("parameters", {})
    for param_name, param_type in required_params.items():
        if param_name not in inputs:
            return False
    return True

def execute_tool_plan(routing_decision: ToolRoutingDecision) -> ToolExecutionTrace:
    trace = ToolExecutionTrace()
    
    if not routing_decision.requires_tools:
        return trace

    previous_output = ""
    
    for i, selection in enumerate(routing_decision.selections):
        tool_name = selection.tool_name
        inputs = dict(selection.required_inputs)
        
        print(f"\n[EXECUTOR] Executing Step {i+1}: {tool_name}")
        print(f"  Inputs: {inputs}")
        
        start_time = time.time()
        result = ToolExecutionResult(tool_name=tool_name, success=False)
        
        if tool_name not in AVAILABLE_TOOLS:
            result.error = f"Unknown tool: {tool_name}"
            print(f"  [ERROR] {result.error}")
        elif not validate_inputs(tool_name, inputs):
            result.error = f"Input validation failed for {tool_name}. Required: {AVAILABLE_TOOLS[tool_name]['parameters']}"
            print(f"  [ERROR] {result.error}")
        else:
            handler = AVAILABLE_TOOLS[tool_name].get("handler")
            try:
                # Basic multi-tool pipeline feature: if the tool accepts 'previous_output'
                sig = inspect.signature(handler)
                if 'previous_output' in sig.parameters and previous_output:
                    inputs['previous_output'] = previous_output
                    
                output = handler(**inputs)
                result.success = True
                result.output = str(output)
                previous_output = result.output
                print(f"  [SUCCESS] Output length: {len(result.output)}")
            except Exception as e:
                result.error = str(e)
                print(f"  [EXCEPTION] {result.error}")
                
        result.execution_time_ms = (time.time() - start_time) * 1000
        trace.results.append(result)
        
        if not result.success:
            trace.overall_success = False
            trace.failed_step = tool_name
            if "ignore" not in routing_decision.fallback_strategy.lower():
                print(f"[EXECUTOR] Halting multi-tool execution due to failure in {tool_name}")
                break
                
    if trace.results:
        trace.final_output = trace.results[-1].output if trace.results[-1].success else trace.results[-1].error
        
    return trace
