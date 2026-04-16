import os
import sys
import json
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.planning.planner import generate_optimized_plan
from apps.backend.agent.world_model import simulate_candidate_action
from apps.backend.schemas.simulation import SimulationResult
from apps.backend.schemas.plan import Plan, PlanStep

def mock_planner(messages, model):
    if "Plan 0" in messages[1]["content"]:
        return "" # Force fallback
    return json.dumps({"title": "Mock Plan", "steps": [{"title": "step1", "order_index": 1}]})

def mock_simulation(messages, model):
    input_text = messages[1]["content"]
    
    if "Malformed" in input_text:
        return "Garbage Data"
        
    if "High Risk Strategy" in input_text:
        return json.dumps({
            "success_probability": 0.4,
            "risk_score": 0.9,
            "recommendation_score": 0.2
        })
        
    if "Safe Strategy" in input_text:
         return json.dumps({
            "success_probability": 0.9,
            "risk_score": 0.1,
            "recommendation_score": 0.9
        })
        
    return json.dumps({
        "success_probability": 0.8,
        "risk_score": 0.3,
        "recommendation_score": 0.8
    })

def run_verification():
    print("=== TONY WORLD MODEL SIMULATION VERIFICATION (PART 8P) ===\n")
    
    with patch("apps.backend.agent.world_model.run_llm_inference", side_effect=mock_simulation), \
         patch("apps.backend.planning.planner.run_llm_inference", side_effect=mock_planner):

        print("[TEST A, F] Simulation Extraction & Safe Fallback")
        # Simulates extraction natively avoiding garbage faults
        res_safe = simulate_candidate_action("c1", "Malformed Plan", context={"a": 1})
        assert res_safe.recommendation_score == 0.1
        assert res_safe.risk_score == 0.9
        print("Tests A, F Passed\n")
        
        print("[TEST B, C] Comparative Ranking (Risk penalization)")
        # Manually comparing via world model engine directly simulating the core feature
        from apps.backend.agent.world_model import compare_candidate_plans
        plans = [
            Plan(id="safe", user_goal="", title="Safe Strategy", steps=[]),
            Plan(id="risky", user_goal="", title="High Risk Strategy", steps=[])
        ]
        comparison = compare_candidate_plans(plans, context={})
        assert comparison[0].candidate_id == "safe"
        assert comparison[1].candidate_id == "risky"
        assert comparison[1].risk_score > comparison[0].risk_score
        assert comparison[0].recommendation_score > comparison[1].recommendation_score
        print("Tests B, C Passed\n")
        
        print("[TEST D, E] Planner Optimization Hook & Logging Validation")
        # Now prove the planner natively hooks into it to drop the bad candidate
        def dynamic_mock_plans(*args, **kwargs):
             dynamic_mock_plans.counter += 1
             title = "High Risk Strategy" if dynamic_mock_plans.counter == 1 else "Safe Strategy"
             p = Plan(id=f"plan_{dynamic_mock_plans.counter}", user_goal="Demo", title=title, steps=[PlanStep(id=f"s{dynamic_mock_plans.counter}", title="Step", description="Mock step", order_index=1)])
             return p
        dynamic_mock_plans.counter = 0
             
        with patch("apps.backend.planning.planner.generate_execution_plan", side_effect=dynamic_mock_plans):
             best_plan = generate_optimized_plan("Execute action")
             assert best_plan.title == "Safe Strategy"
        print("Tests D, E Passed\n")

        print("\n=== RAW WORLD MODEL RANKING DUMP ===")
        print(json.dumps([c.model_dump() for c in comparison], indent=2))

    print("\n=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    run_verification()
