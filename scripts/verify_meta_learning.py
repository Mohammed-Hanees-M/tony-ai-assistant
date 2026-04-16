import os
import sys
import json
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.schemas.learning import PerformanceMetric
from apps.backend.learning.meta_learning_engine import run_meta_learning_cycle

def mock_inference(messages, model):
    content = messages[1]["content"]
    
    if "world_model" not in content and "memory_engine" not in content:
        return "[]"
        
    return json.dumps([
        {
            "title": "Fix Memory Engine Leaks",
            "affected_subsystem": "memory_engine",
            "observed_problem": "Success rate 0.4",
            "hypothesis": "Context overflowing token limit.",
            "suggested_fix": "Implement sliding window correctly.",
            "confidence": 0.8,
            "risk_level": "high"
        },
        {
            "title": "Fix World Model Fallback",
            "affected_subsystem": "world_model",
            "observed_problem": "Fallback rate 0.5",
            "hypothesis": "JSON parsing fails.",
            "suggested_fix": "Extract JSON cleanly.",
            "confidence": 0.95,
            "risk_level": "low"
        }
    ])

def run_verification():
    print("=== TONY META-LEARNING ENGINE VERIFICATION (PART 8Q) ===\n")
    
    with patch("apps.backend.learning.meta_learning_engine.run_llm_inference", side_effect=mock_inference):

        metrics_mixed = [
            PerformanceMetric(subsystem_name="planner", success_rate=0.99, avg_latency=100.0, error_count=0, fallback_rate=0.01, confidence_calibration_error=0.05),
            PerformanceMetric(subsystem_name="world_model", success_rate=0.85, avg_latency=1500.0, error_count=2, fallback_rate=0.5, confidence_calibration_error=0.1),
            PerformanceMetric(subsystem_name="memory_engine", success_rate=0.4, avg_latency=300.0, error_count=10, fallback_rate=0.2, confidence_calibration_error=0.5)
        ]
        
        print("[TEST A, B, C] Aggregate, Detect, Generate")
        proposals = run_meta_learning_cycle(metrics_mixed)
        assert len(proposals) == 2, "Failed to isolate exactly 2 unhealthy systems"
        
        # Test D: Ranking works properly (confidence descending, risk ascending)
        print("[TEST D] Opportunity Ranking")
        assert proposals[0].title == "Fix World Model Fallback" # 0.95 conf, low risk
        assert proposals[1].title == "Fix Memory Engine Leaks" # 0.8 conf, high risk
        print("Tests A, B, C, D Passed\n")
        
        # Test E & F: Safe behavior / healthy ignores
        print("[TEST E, F] Ignore Healthy Architecture")
        metrics_healthy = [
             PerformanceMetric(subsystem_name="planner", success_rate=0.99, avg_latency=100.0, error_count=0, fallback_rate=0.01, confidence_calibration_error=0.05)
        ]
        healthy_props = run_meta_learning_cycle(metrics_healthy)
        assert len(healthy_props) == 0, "Generated proposal for healthy system!"
        print("Tests E, F Passed\n")
        
        print("\n=== RAW IMPROVEMENT OPPORTUNITIES DUMP ===")
        print(json.dumps([p.model_dump() for p in proposals], indent=2))

    print("\n=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    run_verification()
