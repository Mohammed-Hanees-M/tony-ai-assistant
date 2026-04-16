import os
import sys
import json
from unittest.mock import patch, MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.cognition.cognitive_controller import run_tony

def mock_inference(messages, model):
    user_content = messages[1]["content"] if len(messages) > 1 else ""
    
    if "Simple" in user_content:
        return json.dumps({
            "pipeline_mode": "direct",
            "required_modules": ["memory", "reasoning"],
            "execution_order": [
                {"module_name": "memory", "description": "1", "order_index": 1},
                {"module_name": "reasoning", "description": "2", "order_index": 2}
            ]
        })
        
    if "Specialist" in user_content:
        return json.dumps({
            "pipeline_mode": "multi_agent",
            "required_modules": ["memory", "multi_agent"],
            "execution_order": [
                {"module_name": "memory", "description": "1", "order_index": 1},
                {"module_name": "multi_agent", "description": "2", "order_index": 2}
            ]
        })
        
    if "Complex" in user_content:
        return json.dumps({
            "pipeline_mode": "autonomous",
            "required_modules": ["memory", "autonomous_loop"],
            "execution_order": [
                {"module_name": "memory", "description": "1", "order_index": 1},
                {"module_name": "autonomous_loop", "description": "2", "order_index": 2}
            ]
        })

    return "{}"

# Mocked Subsystems
mock_reasoner = MagicMock(return_value="Reasoned Result")
mock_multi_agent = MagicMock(return_value={"final_output": "MultiAgent Result"})
mock_auto_loop = MagicMock(return_value=MagicMock(status="success"))

def run_verification():
    print("=== TONY UNIFIED EXECUTIVE VERIFICATION (PART 8U) ===\n")
    
    with patch("apps.backend.cognition.cognitive_controller.run_llm_inference", side_effect=mock_inference), \
         patch("apps.backend.cognition.cognitive_controller.generate_reasoned_response", mock_reasoner), \
         patch("apps.backend.cognition.cognitive_controller.run_multi_agent_workflow", mock_multi_agent), \
         patch("apps.backend.cognition.cognitive_controller.run_autonomous_task", mock_auto_loop):

        # A. Simple -> Direct
        print("[TEST A] Unified Entry: Simple Query -> Direct Response")
        trace_a = run_tony("Simple question", {})
        assert trace_a.plan.pipeline_mode == "direct"
        assert "reasoning" in trace_a.module_outputs
        print("Test A Passed\n")
        
        # B. Specialist -> Multi-Agent
        print("[TEST B] Unified Entry: Specialist Query -> Multi-Agent Workflow")
        trace_b = run_tony("Specialist coding task", {})
        assert trace_b.plan.pipeline_mode == "multi_agent"
        assert "multi_agent" in trace_b.module_outputs
        print("Test B Passed\n")
        
        # C. Complex -> Autonomous Loop
        print("[TEST C] Unified Entry: Complex Goal -> Autonomous Loop")
        trace_c = run_tony("Complex long-running task", {})
        assert trace_c.plan.pipeline_mode == "autonomous"
        assert "autonomous_loop" in trace_c.module_outputs
        print("Test C Passed\n")
        
        # E. Trace Preservation
        print("[TEST E] Trace Preservation across modes")
        assert trace_c.plan.execution_order[0].module_name == "memory"
        assert len(trace_c.execution_timings) == 2
        print("Test E Passed\n")

        print("\n=== FINAL UNIFIED TRACE DUMP (Test C) ===")
        print(json.dumps(trace_c.model_dump(), indent=2, default=str))

    print("\n=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    run_verification()
