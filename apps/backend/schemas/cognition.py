from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
import time

class CognitiveStep(BaseModel):
    module_name: str
    description: str = "Automated cognitive step"
    order_index: int = 1 # Default to 1 to prevent validation crashes
    required: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)

class CognitiveExchange(BaseModel):
    source_module: str
    payload: Any
    confidence: float = 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)

class CognitivePlan(BaseModel):
    pipeline_mode: str # direct, multi_agent, autonomous
    required_modules: List[str]
    execution_order: List[CognitiveStep]
    reasoning_depth: str = "shallow" # shallow, standard, deep
    estimated_complexity: str = "low" # low, medium, high
    risk_level: str = "low" # low, medium, high
    routing_reason: str = "N/A"
    budgets: Dict[str, Any] = Field(default_factory=lambda: {
        "max_latency_ms": 10000,
        "max_tokens": 4000,
        "max_tool_calls": 5,
        "max_recursion_depth": 2,
        "max_debate_rounds": 1
    })

class CognitiveTrace(BaseModel):
    plan: CognitivePlan
    execution_timings: Dict[str, float] = Field(default_factory=dict)
    module_outputs: Dict[str, CognitiveExchange] = Field(default_factory=dict)
    skipped_modules: List[Dict[str, str]] = Field(default_factory=list)
    cache_stats: Dict[str, int] = Field(default_factory=lambda: {"hits": 0, "misses": 0})
    parallel_speedup_ms: float = 0.0
    total_latency_ms: float = 0.0
    resolved_query: Optional[str] = None
    final_result: Any = None
