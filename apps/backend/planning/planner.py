import json
import uuid
import re
from apps.backend.schemas.plan import Plan, PlanStep, Subtask
from apps.backend.llm.inference import run_llm_inference
from apps.backend.agent.world_model import compare_candidate_plans
from apps.backend.utils.json_parser import safe_parse_json

PLANNING_PROMPT = """
You are Tony's Goal Decomposition Engine. Your job is to take a complex user goal and break it down into a highly structured executable plan.
You must return your output strictly as a JSON object, adhering to the following structure:
{
  "title": "A short descriptive title for the plan",
  "steps": [
    {
      "title": "Step 1 Title",
      "description": "What needs to be done",
      "order_index": 1,
      "dependencies": [],
      "estimated_complexity": "low|medium|high",
      "subtasks": [
        {
          "title": "Subtask 1 Title",
          "description": "Details",
          "order_index": 1,
          "estimated_complexity": "low"
        }
      ]
    }
  ]
}

Ensure all steps and subtasks have an order_index.
If dependencies exist among steps, list their order_index integers in the "dependencies" array.
Do not wrap your response in markdown code blocks, just raw JSON.
"""

def extract_json(raw_text: str) -> str:
    """Extracts JSON block from raw text if wrapped in markdown."""
    try:
        match = re.search(r'```(?:json)?\s*(.*?)\s*```', raw_text, re.DOTALL)
        if match:
            return match.group(1)
        # Attempt to find the first { and last }
        start = raw_text.find('{')
        end = raw_text.rfind('}')
        if start != -1 and end != -1:
            return raw_text[start:end+1]
        return raw_text
    except:
        return raw_text

def parse_and_validate_plan(raw_output: str, user_goal: str) -> Plan:
    try:
        data = safe_parse_json(raw_output, fallback={})
        if not data:
            raise ValueError("No valid JSON in output")
        
        # Build Models
        plan_id = str(uuid.uuid4())
        steps = []
        for s_idx, s_data in enumerate(data.get("steps", [])):
            step_id = f"step_{plan_id}_{s_idx}"
            
            subtasks = []
            for sub_idx, sub_data in enumerate(s_data.get("subtasks", [])):
                sub_id = f"sub_{step_id}_{sub_idx}"
                subtasks.append(Subtask(
                    id=sub_id,
                    title=sub_data.get("title", "Unnamed Subtask"),
                    description=sub_data.get("description", ""),
                    order_index=sub_data.get("order_index", sub_idx + 1),
                    parent_step_id=step_id,
                    estimated_complexity=sub_data.get("estimated_complexity"),
                    dependencies=[str(d) for d in sub_data.get("dependencies", [])]
                ))
                
            steps.append(PlanStep(
                id=step_id,
                title=s_data.get("title", "Unnamed Step"),
                description=s_data.get("description", ""),
                order_index=s_data.get("order_index", s_idx + 1),
                dependencies=[str(d) for d in s_data.get("dependencies", [])],
                subtasks=subtasks,
                estimated_complexity=s_data.get("estimated_complexity")
            ))
            
        plan = Plan(
            id=plan_id,
            user_goal=user_goal,
            title=data.get("title", f"Plan for: {user_goal[:20]}..."),
            steps=steps
        )
        print(f"[PLANNER] Validation successful. Generated {len(plan.steps)} steps.")
        return plan
        
    except Exception as e:
        print(f"[PLANNER] Validation failed: {str(e)}. Generating safe fallback plan.")
        # Reject invalid decomposition and fallback
        step_id = str(uuid.uuid4())
        return Plan(
            user_goal=user_goal,
            title="Fallback Plan",
            steps=[
                PlanStep(
                    id=step_id,
                    title="Execute Goal Manually",
                    description="Goal could not be automatically decomposed.",
                    order_index=1
                )
            ]
        )

def generate_execution_plan(user_goal: str, model: str = "phi3") -> Plan:
    """Decomposes a user goal into a structured executable plan."""
    print(f"\n[PLANNER] Analyzing goal: '{user_goal}'")
    
    messages = [
        {"role": "system", "content": PLANNING_PROMPT},
        {"role": "user", "content": f"Decompose this goal: {user_goal}"}
    ]
    
    raw_response = run_llm_inference(messages, model)
    print(f"[PLANNER] Raw output received. Length: {len(raw_response)}")
    
    plan = parse_and_validate_plan(raw_response, user_goal)
    return plan

def generate_optimized_plan(user_goal: str, num_candidates: int = 2, model: str = "phi3") -> Plan:
    print(f"\n[PLANNER] Generating {num_candidates} candidate plans for: '{user_goal}'")
    candidates = []
    for _ in range(num_candidates):
        plan = generate_execution_plan(user_goal, model)
        candidates.append(plan)
        
    print(f"[PLANNER] Evaluating candidates via World Model...")
    simulations = compare_candidate_plans(candidates, context={"user_goal": user_goal}, model=model)
    
    best_sim = simulations[0]
    best_plan = next(p for p in candidates if p.id == best_sim.candidate_id)
    
    print(f"[PLANNER] Selected Plan '{best_plan.title}' (Recommendation: {best_sim.recommendation_score})")
    
    # Inject simulation data directly into the plan metadata conceptually (since Plan schema is tightly bound, we will trace it via print)
    return best_plan
