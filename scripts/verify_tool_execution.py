import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.schemas.tool import ToolRoutingDecision, ToolSelection
from apps.backend.tools.tool_executor import execute_tool_plan

def run_verification():
    print("=== TONY TOOL EXECUTION VERIFICATION (PART 8E) ===\n")
    
    # A. Single tool executes correctly & C. Outputs captured properly
    decision_single = ToolRoutingDecision(
        requires_tools=True,
        selections=[
            ToolSelection(tool_name="web_search", reason="test", required_inputs={"query": "test query"})
        ],
        fallback_strategy="abort",
        reasoning_summary="Single tool test"
    )
    trace_a = execute_tool_plan(decision_single)
    assert trace_a.overall_success is True
    assert len(trace_a.results) == 1
    assert trace_a.final_output == "Search results for: test query"
    print("Test A & C: Single tool execution and output capture passed.\n")
    
    # B. Multi-tool sequential
    decision_multi = ToolRoutingDecision(
        requires_tools=True,
        selections=[
            ToolSelection(tool_name="document_reader", reason="step 1", required_inputs={"file_path": "data.csv"}),
            ToolSelection(tool_name="python_interpreter", reason="step 2", required_inputs={"code": "process()"})
        ],
        fallback_strategy="abort",
        reasoning_summary="Multi tool test"
    )
    trace_b = execute_tool_plan(decision_multi)
    assert trace_b.overall_success is True
    assert len(trace_b.results) == 2
    assert trace_b.results[0].tool_name == "document_reader"
    assert "Contents" in trace_b.results[0].output
    print("Test B: Multi-tool sequential pipeline passed.\n")
    
    # D. Input validation fails bad payloads
    decision_invalid = ToolRoutingDecision(
        requires_tools=True,
        selections=[
            ToolSelection(tool_name="web_search", reason="missing param", required_inputs={"wrong_param": "foo"})
        ],
        fallback_strategy="ignore",
        reasoning_summary="Invalid test"
    )
    trace_d = execute_tool_plan(decision_invalid)
    assert trace_d.overall_success is False
    assert "Input validation failed" in trace_d.results[0].error
    print("Test D: Input validation blocked bad payloads safely.\n")
    
    # E. Tool failure isolated safely
    decision_fail = ToolRoutingDecision(
        requires_tools=True,
        selections=[
            ToolSelection(tool_name="document_reader", reason="step 1 fails", required_inputs={"file_path": "bad.txt"}),
            ToolSelection(tool_name="python_interpreter", reason="step 2 skipped", required_inputs={"code": "process()"})
        ],
        fallback_strategy="abort",
        reasoning_summary="Failure isolation test"
    )
    trace_e = execute_tool_plan(decision_fail)
    assert trace_e.overall_success is False
    assert trace_e.failed_step == "document_reader"
    assert len(trace_e.results) == 1 # Execution halted
    print("Test E: Tool failure isolated and halted execution safely.\n")
    
    # F. Execution trace generated
    print("Test F: Execution trace dump excerpt:")
    print(trace_b.model_dump_json(indent=2))
    
    print("\n=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    run_verification()
