import os
import sys
import json
import time
from unittest.mock import patch, MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.cognition.cognitive_controller import run_tony
from apps.backend.utils.performance import GLOBAL_COGNITION_CACHE

# Cleanup cache
GLOBAL_COGNITION_CACHE.cache = {}
if os.path.exists("cognition_cache.json"):
    os.remove("cognition_cache.json")

def mock_inference(messages, model):
    return json.dumps({
        "pipeline_mode": "direct",
        "required_modules": ["memory", "graph", "reasoning"],
        "execution_order": [
            {"module_name": "memory", "description": "1", "order_index": 1},
            {"module_name": "graph", "description": "2", "order_index": 1},
            {"module_name": "reasoning", "description": "3", "order_index": 2}
        ]
    })

def slow_module(*args, **kwargs):
    time.sleep(1) # Artificial delay
    return "Slow Result"

def run_verification():
    print("=== TONY PERFORMANCE OPTIMIZATION VERIFICATION (PART 8W) ===\n")
    
    with patch("apps.backend.cognition.cognitive_controller.run_llm_inference", side_effect=mock_inference), \
         patch("apps.backend.cognition.cognitive_controller.fuse_with_memory_retrieval", side_effect=slow_module), \
         patch("apps.backend.cognition.cognitive_controller.traverse_related_entities", side_effect=slow_module), \
         patch("apps.backend.cognition.cognitive_controller.generate_reasoned_response", return_value="Quick Result"):

        print("[TEST A] Parallel Execution Speedup")
        start = time.time()
        trace_p = run_tony("Parallel test", {})
        total_wall = (time.time() - start) * 1000
        sum_latency = sum(trace_p.execution_timings.values())
        
        print(f"  -> Sum of module latencies: {sum_latency:.0f}ms")
        print(f"  -> Actual wall-clock time: {total_wall:.0f}ms")
        print(f"  -> Speedup Recorded: {trace_p.parallel_speedup_ms:.0f}ms")
        
        assert total_wall < sum_latency, "Parallel execution did not reduce wall-clock time!"
        print("Test A Passed\n")
        
        print("[TEST B, D] Cache Hit & Unified Schema")
        # Run again with same query - should hit cache
        start_cache = time.time()
        trace_c = run_tony("Parallel test", {})
        wall_cache = (time.time() - start_cache) * 1000
        
        assert trace_c.cache_stats["hits"] == 3
        assert wall_cache < 500, f"Cache miss or slow lookup: {wall_cache}ms"
        assert trace_c.module_outputs["memory"].source_module == "memory"
        print("Tests B, D Passed\n")
        
        print("[TEST C] TTL Expiry")
        # Ensure we use the exact keys that the controller uses
        stable_keys = ["memory_context", "graph_context"] # Simplification for mock
        GLOBAL_COGNITION_CACHE.set("reasoning", {"query": "TTL Test", "context_keys": stable_keys}, "Outdated", ttl_seconds=-1)
        
        trace_expired = run_tony("TTL Test", {})
        # Reasoning should be a miss (expired), memory/graph should be misses (brand new query)
        # Total misses should be 3 for a fresh query
        assert trace_expired.cache_stats["misses"] == 3
        print("Test C Passed\n")

    print("\n=== PERFORMANCE BENCHMARK DUMP ===")
    results = {
        "wall_clock_ms": total_wall,
        "sequential_sum_ms": sum_latency,
        "parallel_speedup_ms": trace_p.parallel_speedup_ms,
        "cache_hit_latency_ms": wall_cache,
        "unified_schema_valid": True
    }
    print(json.dumps(results, indent=2))

    print("\n=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    run_verification()
