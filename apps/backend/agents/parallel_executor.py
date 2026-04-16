import time
import concurrent.futures
from typing import List, Dict
from apps.backend.schemas.agent import SpecialistResult, SpecialistProfile
from apps.backend.agents.specialist_registry import get_specialist
from apps.backend.agents.subagent_executor import execute_specialist_task

def _run_single(specialist: SpecialistProfile, query: str, model: str) -> SpecialistResult:
    start_time = time.time()
    try:
        result = execute_specialist_task(specialist, query, model)
        result.metadata["execution_time_ms"] = (time.time() - start_time) * 1000
        result.metadata["failed"] = False
        result.metadata["timeout_occurred"] = False
        return result
    except Exception as e:
        exec_time = (time.time() - start_time) * 1000
        print(f"[PARALLEL EXECUTOR] Specialist '{specialist.name}' raised internal exception: {e}")
        return SpecialistResult(
            specialist_id=specialist.id,
            subtask=query,
            output=f"Failed due to error: {e}",
            confidence=0.0,
            metadata={"execution_time_ms": exec_time, "failed": True, "timeout_occurred": False}
        )

def execute_specialists_parallel(assignments: List[Dict], query: str, model: str = "phi3", timeout_sec: float = 10.0) -> List[SpecialistResult]:
    """
    Executes sub-agents in parallel using ThreadPoolExecutor.
    Preserves input priority ordering (assignments should be sorted by priority).
    """
    print(f"[PARALLEL EXECUTOR] Preparing {len(assignments)} assignments for parallel execution...")
    
    results: List[SpecialistResult] = [None] * len(assignments)
    
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(assignments)))
    future_to_index = {}
    for index, sel in enumerate(assignments):
        spec_id = sel.get("specialist_id")
        specialist = get_specialist(spec_id)
        if not specialist:
            print(f"[PARALLEL EXECUTOR] Invalid specialist {spec_id}. Skipping.")
            results[index] = SpecialistResult(
                specialist_id=spec_id or "unknown",
                subtask=query,
                output="Specialist not found in registry.",
                confidence=0.0,
                metadata={"execution_time_ms": 0.0, "failed": True, "timeout_occurred": False}
            )
            continue
            
        future = executor.submit(_run_single, specialist, query, model)
        future_to_index[future] = (index, specialist)
        
    start_wait = time.time()
    try:
        for future in concurrent.futures.as_completed(future_to_index.keys(), timeout=timeout_sec):
            index, specialist = future_to_index[future]
            try:
                results[index] = future.result()
            except Exception as exc:
                print(f"[PARALLEL EXECUTOR] Unexpected exception retrieving future for {specialist.name}: {exc}")
                results[index] = SpecialistResult(
                    specialist_id=specialist.id,
                    subtask=query,
                    output="Fatal threading exception.",
                    confidence=0.0,
                    metadata={"execution_time_ms": (time.time() - start_wait)*1000, "failed": True, "timeout_occurred": False}
                )
    except concurrent.futures.TimeoutError:
        print(f"[PARALLEL EXECUTOR] Timeout limit ({timeout_sec}s) reached. Processing partial results.")
            
    executor.shutdown(wait=False, cancel_futures=True)
    
    # Handle any tasks that didn't complete (meaning they timed out)
    for future, (index, specialist) in future_to_index.items():
        if results[index] is None:
            print(f"[PARALLEL EXECUTOR] Specialist '{specialist.name}' TIMED OUT.")
            results[index] = SpecialistResult(
                specialist_id=specialist.id,
                subtask=query,
                output=f"Execution timed out after {timeout_sec} seconds.",
                confidence=0.0,
                metadata={"execution_time_ms": timeout_sec * 1000, "failed": True, "timeout_occurred": True}
            )
                
    # Filter out pure Nones just in case (should not happen with list pre-allocation)
    return [r for r in results if r is not None]
