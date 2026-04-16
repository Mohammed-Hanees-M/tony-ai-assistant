from pydantic import BaseModel, Field
from typing import List, Optional
import uuid

class ReasoningStep(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    thought: str
    rationale: str
    intermediate_result: Optional[str] = None
    order_index: int

class ReasoningTrace(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query: str
    steps: List[ReasoningStep] = Field(default_factory=list)
    final_conclusion: str
    confidence: float = Field(default=1.0)

class VerificationReport(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    passed: bool
    confidence_delta: float = Field(default=0.0)
    issues_found: List[str] = Field(default_factory=list)
    suggested_improvements: List[str] = Field(default_factory=list)
    revised_answer: str
    verifier_notes: str

