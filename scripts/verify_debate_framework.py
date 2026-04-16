import os
import sys
import json
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.agents.multi_agent_orchestrator import run_multi_agent_workflow

def mock_delegation(query, model):
    if "Debate" in query:
        return [
            {"specialist_id": "coding_expert", "priority": 1},
            {"specialist_id": "research_expert", "priority": 2}
        ]
    return [{"specialist_id": "writing_expert", "priority": 1}]

def mock_execute(sel, query, model):
    from apps.backend.schemas.agent import SpecialistResult
    if sel.id == "coding_expert":
        return SpecialistResult(specialist_id=sel.id, subtask=query, output="Use Python 2 as it's the fastest.", confidence=0.9)
    if sel.id == "research_expert":
        return SpecialistResult(specialist_id=sel.id, subtask=query, output="Python 2 is dead. Use Python 3.", confidence=0.9)
    return SpecialistResult(specialist_id=sel.id, subtask=query, output="Safe output.", confidence=0.8)

def mock_inference(messages, model):
    if "Conflict Detector" in messages[0]["content"]:
        # Let's say debate test triggers conflict
        if "Python 2" in messages[1]["content"]:
            return json.dumps({
                "conflict_detected": True,
                "reason": "Versions conflict explicitly.",
                "conflicting_specialists": ["coding_expert", "research_expert"]
            })
        return json.dumps({"conflict_detected": False})
        
    if "You are the" in messages[0]["content"] and "critique" in messages[1]["content"]:
        return "I disagree severely."
        
    if "Arbitrator" in messages[0]["content"]:
        return json.dumps({
            "resolution_summary": "Use Python 3.",
            "winning_position": "research_expert",
            "confidence_adjustment": 0.5
        })
        
    if "Coordinator" in messages[0]["content"]:
        return "Aggregated response."
        
    return "Default mock"

def run_verification():
    print("=== TONY DEBATE / CROSS VERIFICATION (PART 8N) ===\n")
    
    with patch("apps.backend.agents.multi_agent_orchestrator.select_specialists_for_task", side_effect=mock_delegation), \
         patch("apps.backend.agents.multi_agent_orchestrator.execute_specialists_parallel", side_effect=lambda a,b,c: [mock_execute(s,b,c) for s in [__import__("apps.backend.agents.specialist_registry", fromlist=[""]).get_specialist(x["specialist_id"]) for x in a]]), \
         patch("apps.backend.agents.debate_engine.run_llm_inference", side_effect=mock_inference), \
         patch("apps.backend.agents.multi_agent_orchestrator.run_llm_inference", side_effect=mock_inference):

        # Test A-E: Conflict triggers debate, checks, and resolves
        print("[TEST A, B, C, D, E] Debate Flow")
        res = run_multi_agent_workflow("Debate Topic")
        
        db_res = res["debate_result"]
        assert db_res["conflict_detected"] == True
        assert len(db_res["critiques"]) == 2 # 2 participants means 2 cross critiques
        assert db_res["winning_position"] == "research_expert"
        assert db_res["confidence_adjustment"] == 0.5
        print("Debate Flow Tests Passed\n")
        
        # Test F: Skip debate when 1 participant or no conflict
        print("[TEST F] Safe Skipped Debate Flow")
        safe_res = run_multi_agent_workflow("Safe Action")
        assert safe_res["debate_result"]["conflict_detected"] == False
        print("Test F Passed\n")
        
        print("\n=== RAW DEBATE RESULT DUMP ===")
        print(json.dumps(res["debate_result"], indent=2))

    print("\n=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    run_verification()
