from pydantic import BaseModel
from typing import List

class PerformanceMetric(BaseModel):
    subsystem_name: str
    success_rate: float
    avg_latency: float
    error_count: int
    fallback_rate: float
    confidence_calibration_error: float

class ImprovementProposal(BaseModel):
    title: str
    affected_subsystem: str
    observed_problem: str
    hypothesis: str
    suggested_fix: str
    confidence: float
    risk_level: str
