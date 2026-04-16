import os
import sys
import json
from unittest.mock import patch

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.planning.planner import generate_execution_plan, parse_and_validate_plan

VALID_JSON_RESPONSE = """
```json
{
  "title": "Set up Web Server",
  "steps": [
    {
      "title": "Install Dependencies",
      "description": "Install fastapi and uvicorn",
      "order_index": 1,
      "dependencies": [],
      "estimated_complexity": "low",
      "subtasks": [
        {
          "title": "Run pip install",
          "description": "pip install uvicorn fastapi",
          "order_index": 1,
          "estimated_complexity": "low"
        }
      ]
    },
    {
      "title": "Create main.py",
      "description": "Write basic API routes",
      "order_index": 2,
      "dependencies": [1],
      "estimated_complexity": "medium",
      "subtasks": []
    }
  ]
}
```
"""

INVALID_JSON_RESPONSE = "This is not JSON! I refuse."

def mock_inference(messages, model):
    content = messages[-1]["content"]
    if "FAIL_TEST" in content:
        return INVALID_JSON_RESPONSE
    return VALID_JSON_RESPONSE

def run_verification():
    print("=== TONY PLANNING ENGINE VERIFICATION (PART 8A) ===\n")
    
    with patch("apps.backend.planning.planner.run_llm_inference", side_effect=mock_inference):
        goal = "Create a basic python backend"
        plan = generate_execution_plan(goal)
        
        # A. Complex goal decomposes into multi-step plan
        print(f"Test A: Plan generated with {len(plan.steps)} steps.")
        assert len(plan.steps) == 2, "Failed to create multi-step plan"
        assert plan.title == "Set up Web Server"
        
        # B. Steps are ordered logically
        print("Test B: Steps logically ordered.")
        assert plan.steps[0].order_index == 1
        assert plan.steps[1].order_index == 2
        
        # C. Dependencies represented correctly
        print("Test C: Step 2 dependencies ->", plan.steps[1].dependencies)
        assert "1" in plan.steps[1].dependencies, "Dependency missing"
        
        # D. Nested subtasks supported
        print(f"Test D: Step 1 has {len(plan.steps[0].subtasks)} subtasks (expected: 1).")
        assert len(plan.steps[0].subtasks) == 1
        assert plan.steps[0].subtasks[0].title == "Run pip install"
        
        # E. Invalid planner output handled safely
        print("\n[Simulating Invalid Output]")
        safe_plan = generate_execution_plan("FAIL_TEST")
        print(f"Test E: Invalid output plan title: '{safe_plan.title}'")
        assert safe_plan.title == "Fallback Plan", "Did not fallback safely."
        assert len(safe_plan.steps) == 1
        assert safe_plan.steps[0].title == "Execute Goal Manually"
        
        print("\n=== RAW PLAN DUMP ===")
        print(plan.model_dump_json(indent=2))

    print("\n=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    run_verification()
