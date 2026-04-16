from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
import uuid
import time

# Assume these exist from prior phases
from apps.backend.schemas.plan import Plan, PlanStep
from apps.backend.schemas.tool import ToolExecutionTrace

class ApprovalDecision(BaseModel):
    approved: bool
    modified_step: Optional[PlanStep] = None
    notes: str = ""
    decided_at: float = Field(default_factory=time.time)

class ApprovalCheckpoint(BaseModel):
    checkpoint_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    reason: str
    pending_step: PlanStep
    risk_level: str
    requested_at: float = Field(default_factory=time.time)
    decision: Optional[ApprovalDecision] = None

class AutonomousTaskState(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_goal: str
    current_plan: Optional[Plan] = None
    completed_steps: List[str] = Field(default_factory=list)
    failed_steps: List[str] = Field(default_factory=list)
    approved_steps: List[str] = Field(default_factory=list)
    replan_count: int = 0
    failure_history: List[Dict[str, Any]] = Field(default_factory=list)
    iteration_count: int = 0
    status: str = "initialized"
    execution_history: List[ToolExecutionTrace] = Field(default_factory=list)
    pending_checkpoint: Optional[ApprovalCheckpoint] = None
    audit_trail: List[ApprovalCheckpoint] = Field(default_factory=list)

class SpecialistProfile(BaseModel):
    id: str
    name: str
    domain: str
    description: str
    capability_tags: List[str]
    can_manage_subtasks: bool = False
    child_specialist_tags: List[str] = Field(default_factory=list)

class SpecialistResult(BaseModel):
    specialist_id: str
    subtask: str
    output: str
    confidence: float
    metadata: Dict[str, Any] = Field(default_factory=dict)

class Critique(BaseModel):
    critiquer_id: str
    target_id: str
    critique_text: str
    proposed_resolution: str

class DebateResult(BaseModel):
    conflict_detected: bool
    participants: List[str] = Field(default_factory=list)
    critiques: List[Critique] = Field(default_factory=list)
    resolution_summary: str = ""
    winning_position: Optional[str] = None
    confidence_adjustment: float = 0.0

class DelegationNode(BaseModel):
    node_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    specialist_id: str
    query: str
    children: List['DelegationNode'] = Field(default_factory=list)
    result: Optional[SpecialistResult] = None
    depth: int
    parent_node_id: Optional[str] = None

DelegationNode.model_rebuild()
