from pydantic import BaseModel, Field
from typing import List, Optional
import uuid

class Subtask(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    order_index: int
    status: str = Field(default="pending")
    dependencies: List[str] = Field(default_factory=list)
    parent_step_id: str
    estimated_complexity: Optional[str] = None

class PlanStep(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    order_index: int
    status: str = Field(default="pending")
    dependencies: List[str] = Field(default_factory=list)
    subtasks: List[Subtask] = Field(default_factory=list)
    estimated_complexity: Optional[str] = None

class Plan(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    user_goal: str
    steps: List[PlanStep] = Field(default_factory=list)
    status: str = Field(default="created")
