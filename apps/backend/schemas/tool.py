from pydantic import BaseModel, Field
from typing import List, Dict, Any

class ToolSelection(BaseModel):
    tool_name: str
    confidence: float = Field(default=1.0)
    reason: str
    required_inputs: Dict[str, Any] = Field(default_factory=dict)

class ToolRoutingDecision(BaseModel):
    requires_tools: bool
    selections: List[ToolSelection] = Field(default_factory=list)
    fallback_strategy: str = ""
    reasoning_summary: str = ""

class ToolExecutionResult(BaseModel):
    tool_name: str
    success: bool
    output: str = ""
    error: str = ""
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ToolExecutionTrace(BaseModel):
    results: List[ToolExecutionResult] = Field(default_factory=list)
    overall_success: bool = True
    final_output: str = ""
    failed_step: str = ""

class ToolReflection(BaseModel):
    lesson: str
    context_pattern: str
    tool_pattern: str
    success_case: bool
    confidence: float = Field(default=0.5)
    supporting_examples: List[str] = Field(default_factory=list)

