import os
import sys
import time
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.cognition.cognitive_controller import get_brain_controller

def run_verification():
    print("=== TONY ADAPTIVE VOICE ROUTING AUDIT ===\n")
    brain = get_brain_controller()

    test_cases = [
        {
            "query": "Hey Tony, can you hear me?",
            "expected_mode": "direct",
            "reasoning_expected": False,
            "description": "Casual greeting / check"
        },
        {
            "query": "What is 25 * 17?",
            "expected_mode": "direct", # reasoning is a module, but pipeline_mode might be direct
            "reasoning_expected": True,
            "description": "Calculation requiring logic"
        },
        {
            "query": "Who are you?",
            "expected_mode": "direct",
            "reasoning_expected": False,
            "description": "Identity check (Fast-Path candidate)"
        }
    ]

    for case in test_cases:
        print(f"[TEST] Query: '{case['query']}' ({case['description']})")
        start = time.time()
        
        # We look at the generated plan
        plan = brain._generate_plan(case['query'], {})
        latency = (time.time() - start) * 1000
        
        print(f"  -> Mode: {plan.pipeline_mode}")
        print(f"  -> Required Modules: {plan.required_modules}")
        print(f"  -> Latency: {latency:.2f}ms")
        
        # Validation
        modules = [s.module_name for s in plan.execution_order]
        has_reasoning = "reasoning" in modules
        
        if case['reasoning_expected']:
            assert has_reasoning, f"Expected reasoning for query: {case['query']}"
        else:
            assert not has_reasoning, f"Unexpected reasoning for query: {case['query']}"
            
        if "Fast-Path" in case['description']:
            assert latency < 500, "Fast-path triggered but latency too high!"

        print("  -> PASSED\n")

    print("=== AUDIT SUCCESSFUL ===")

if __name__ == "__main__":
    run_verification()
