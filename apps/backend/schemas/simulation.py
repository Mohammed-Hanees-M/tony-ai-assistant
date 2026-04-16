from pydantic import BaseModel, Field
from typing import List

class SimulationResult(BaseModel):
    candidate_id: str
    description: str
    success_probability: float
    risk_score: float
    estimated_latency: float
    estimated_cost: float
    predicted_side_effects: List[str] = Field(default_factory=list)
    predicted_failure_modes: List[str] = Field(default_factory=list)
    recommendation_score: float
