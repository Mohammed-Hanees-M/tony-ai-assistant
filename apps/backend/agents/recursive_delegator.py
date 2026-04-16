import uuid
from typing import Optional
from apps.backend.schemas.agent import DelegationNode, SpecialistProfile, SpecialistResult
from apps.backend.agents.specialist_registry import get_specialist
from apps.backend.agents.delegation_router import select_specialists_for_task
from apps.backend.agents.subagent_executor import execute_specialist_task
from apps.backend.llm.inference import run_llm_inference

def extract_bool(raw: str) -> bool:
    content = raw.lower()
    if 'true' in content or 'yes' in content or 'decompose' in content:
        return True
    return False

def _should_decompose(query: str, spec: SpecialistProfile, model: str) -> bool:
    if not spec.can_manage_subtasks:
        return False
        
    messages = [
        {"role": "system", "content": f"You are a Manager Agent ({spec.id}). Does this task require delegating to multiple sub-specialists to succeed? Reply exactly 'true' or 'false'."},
        {"role": "user", "content": query}
    ]
    raw = run_llm_inference(messages, model)
    return extract_bool(raw)

def run_recursive_delegation(
    query: str, 
    specialist_id: str, 
    model: str = "phi3",
    depth: int = 0,
    parent_node_id: Optional[str] = None,
    max_depth: int = 3,
    budget_counter: dict = None
) -> DelegationNode:
    
    if budget_counter is None:
        budget_counter = {"nodes": 0, "max_nodes": 7}
        
    specialist = get_specialist(specialist_id)
    if not specialist:
        raise ValueError(f"Unknown specialist {specialist_id}")
        
    node_id = str(uuid.uuid4())
    
    node = DelegationNode(
        node_id=node_id,
        specialist_id=specialist_id,
        query=query,
        depth=depth,
        parent_node_id=parent_node_id
    )
    
    budget_counter["nodes"] += 1
    
    prefix = "  " * depth
    print(f"{prefix}[RECR_DELEGATOR] Start node {specialist_id} (Depth {depth}) for query: '{query[:30]}...'")
    
    # 1. Enforce safety limits
    if depth >= max_depth:
        print(f"{prefix}[RECR_DELEGATOR] Max recursion depth ({max_depth}) reached. Forcing flat execution safely.")
        result = execute_specialist_task(specialist, query, model)
        node.result = result
        return node
        
    if budget_counter["nodes"] >= budget_counter["max_nodes"]:
        print(f"{prefix}[RECR_DELEGATOR] Node budget limit exhausted! Forcing flat execution safely.")
        result = execute_specialist_task(specialist, query, model)
        node.result = result
        return node

    # 2. Check if we should decompose
    should_decompose = _should_decompose(query, specialist, model)
    
    if not should_decompose:
        print(f"{prefix}[RECR_DELEGATOR] No decomposition needed. Executing flat task.")
        result = execute_specialist_task(specialist, query, model)
        node.result = result
        return node
        
    # 3. Decompose task
    print(f"{prefix}[RECR_DELEGATOR] Manager {specialist_id} is decomposing task...")
    
    # Heuristically mimicking router delegation mapping
    selections = select_specialists_for_task(query, model)
    
    child_nodes = []
    child_outputs = []
    
    for sel in selections:
        child_id = sel.get("specialist_id")
        child_reason = sel.get("reason", query)
        
        # Guard recursive calling ourself without condition changes natively
        if child_id == specialist_id:
            # We don't want a manager delegating to itself infinitely
            child_node = DelegationNode(
                specialist_id=child_id, query=child_reason, depth=depth+1, parent_node_id=node_id
            )
            child_node.result = execute_specialist_task(specialist, child_reason, model)
            child_nodes.append(child_node)
            child_outputs.append((child_id, child_node.result.output))
            continue
            
        # Recurse downward
        child_node = run_recursive_delegation(
            query=f"{child_reason} (Parent context: {query})",
            specialist_id=child_id,
            model=model,
            depth=depth + 1,
            parent_node_id=node_id,
            max_depth=max_depth,
            budget_counter=budget_counter
        )
        child_nodes.append(child_node)
        if child_node.result:
            child_outputs.append((child_id, child_node.result.output))
            
    node.children = child_nodes
    
    # 4. Aggregate child outputs upward
    print(f"{prefix}[RECR_DELEGATOR] Manager {specialist_id} aggregating {len(child_nodes)} child outputs...")
    
    context_str = "\n".join([f"--- {c_id} ---\n{c_out}" for c_id, c_out in child_outputs])
    agg_msg = [
        {"role": "system", "content": f"You are Manager {specialist_id}. Synthesize child results into a unified answer to '{query}'"},
        {"role": "user", "content": f"Results:\n{context_str}"}
    ]
    agg_raw = run_llm_inference(agg_msg, model)
    
    node.result = SpecialistResult(
        specialist_id=specialist_id,
        subtask=query,
        output=agg_raw.strip(),
        confidence=0.8,
        metadata={"is_manager_aggregate": True, "child_count": len(child_nodes)}
    )
    
    return node
