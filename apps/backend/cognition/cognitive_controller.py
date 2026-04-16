import json
import time
import re
import concurrent.futures
import sys
from typing import Dict, Any, List, Optional, Tuple
from apps.backend.schemas.cognition import CognitivePlan, CognitiveStep, CognitiveTrace, CognitiveExchange
from apps.backend.llm.inference import run_llm_inference
from apps.backend.utils.json_parser import safe_parse_json

# Subsystem Integrations
from apps.backend.reasoning.reasoner import generate_reasoned_response, generate_direct_response
from apps.backend.reasoning.verifier import verify_and_improve_answer
from apps.backend.planning.planner import generate_optimized_plan
from apps.backend.agent.autonomous_loop import run_autonomous_task
from apps.backend.agent.world_model import simulate_candidate_action
from apps.backend.agents.multi_agent_orchestrator import run_multi_agent_workflow
from apps.backend.knowledge.graph_retriever import traverse_related_entities, fuse_with_memory_retrieval
from apps.backend.utilities.system_clock import resolve_temporal_query
from apps.backend.utilities.social_router import resolve_social_query
from apps.backend.utilities.intent_detector import detect_web_requirement
from apps.backend.persona.identity_profile import resolve_identity_query
from apps.backend.conversation.context_manager import get_session_context, update_session_context
from apps.backend.conversation.resolver import resolve_contextual_query, sanitize_response
from apps.backend.conversation.dialogue_act import classify_dialogue_act
from apps.backend.llm.router import select_model
# Performance Utilities
from apps.backend.utils.performance import GLOBAL_COGNITION_CACHE

COGNITIVE_PLANNER_PROMPT = """You are Tony's Central Executive / Brain Controller. 
Analyze the user's query and context. Determine which cognitive modules are required and in what order.

PIPELINE MODES:
1. direct: For casual conversation (greetings, status checks, acknowledgements), simple facts, or chatty responses. 
   - Uses: [memory]
   - ALWAYS use this for queries like "can you hear me?", "hello", "how are you?", "who are you?".
2. multi_agent: For domain-specific tasks (coding, math, research).
   - Uses: [memory, multi_agent]
3. autonomous: For complex tasks requiring tools or planning.
   - Uses: [memory, world_model, autonomous_loop]

ROUTING RULE: 
- If the query is simple, conversational, or a greeting, set pipeline_mode to "direct" and ONLY include the "memory" module.
- DO NOT use "reasoning" for simple questions or chatter to save latency.
- USE "reasoning" ONLY if the query requires step-by-step logic, math, or deep analysis.

Output a JSON CognitivePlan:
{
  "pipeline_mode": "direct|multi_agent|autonomous",
  "required_modules": ["memory"],
  "execution_order": [
    {"module_name": "memory", "description": "Get context", "order_index": 1}
  ],
  "reasoning_depth": "none|shallow|standard|deep",
  "estimated_complexity": "low|medium|high",
  "risk_level": "low|medium|high",
  "budgets": { "max_latency_ms": 30000, "max_tokens": 4000 }
}
"""

class CognitiveController:
    def __init__(self, model: str = "phi3"):
        self.model = model

    def _generate_plan(self, query: str, context: dict, act: str = "QUESTION") -> CognitivePlan:
        """
        Cognitive Latency Optimization Layer:
        Determines the most efficient routing path based on query complexity.
        """
        from apps.backend.utilities.intent_detector import detect_utility_intent
        start_time = time.time()
        q_lower = query.lower().strip()
        
        # --- PHASE 0.0: Deterministic Social Route (URGENT/INSTANT) ---
        social_response = resolve_social_query(q_lower)
        if social_response:
            print(f"[BRAIN] Deterministic Social Route: MATCH")
            return CognitivePlan(
                pipeline_mode="direct",
                routing_reason="Deterministic social match",
                required_modules=["utility"],
                execution_order=[CognitiveStep(module_name="utility", order_index=1)],
                budgets={"max_latency_ms": 100}
            )

        # --- PHASE 0.01: STT Integrity & Coherence Guard ---
        stt_conf = context.get("stt_confidence", 1.0)
        if stt_conf < 0.5 and len(q_lower.split()) > 3:
             print(f"[BRAIN] Low STT Confidence ({stt_conf}). Triggering clarification.")
             return CognitivePlan(
                 pipeline_mode="direct",
                 routing_reason="Low STT confidence / audio incoherence",
                 required_modules=["synthesis"],
                 execution_order=[CognitiveStep(module_name="synthesis", order_index=1)],
                 budgets={"max_latency_ms": 1000}
             )

        # --- PHASE 0: Deterministic Utility Intent (PRE-HEURISTIC) ---
        utility_intent = detect_utility_intent(q_lower)
        if utility_intent:
            print(f"[BRAIN] Deterministic Utility Route: {utility_intent}")
            print(f"[BRAIN] Utility Intent Match Reason: temporal_query_detected")
            return CognitivePlan(
                pipeline_mode="direct",
                routing_reason=f"Semantic utility match: {utility_intent}",
                required_modules=["utility"],
                execution_order=[CognitiveStep(module_name="utility", order_index=1)],
                budgets={"max_latency_ms": 500}
            )
            
        # --- PHASE 0.2: Lightweight Conversational Routing ---
        if act in ["CHITCHAT", "ACKNOWLEDGEMENT"]:
            print(f"[BRAIN] {act} act detected. Routing to lightweight synthesis (Retrieval Bypass).")
            return CognitivePlan(
                pipeline_mode="direct",
                routing_reason=f"Lightweight {act} response",
                required_modules=["synthesis"],
                execution_order=[CognitiveStep(module_name="synthesis", order_index=1)],
                budgets={"max_latency_ms": 1000}
            )

        # --- PHASE 0.35: SIMPLE FOLLOW-UP OPTIMIZATION (No Retrieval) ---
        # Requirement: explain more, give more detail, tell me more -> No graph/semantic retrieval
        simple_followups = ["explain more", "give more detail", "tell me more", "elaborate", "go deeper", "more detail"]
        if any(f in q_lower for f in simple_followups) and act == "FOLLOW_UP":
            print(f"[BRAIN] Simple Follow-Up detected: {q_lower}. Disabling retrieval modules.")
            return CognitivePlan(
                pipeline_mode="direct",
                routing_reason="Simple follow-up retrieval bypass",
                required_modules=["synthesis"],
                execution_order=[
                    CognitiveStep(module_name="synthesis", order_index=1)
                ],
                budgets={"max_latency_ms": 1500}
            )

        # --- PHASE 0.1: Follow-Up Action Optimization ---
        if act == "FOLLOW_UP":
            print("[BRAIN] FOLLOW_UP act detected. Forcing latency-optimized DIRECT_SIMPLE_RESPONSE.")
            return CognitivePlan(
                pipeline_mode="direct",
                routing_reason="Follow-up act optimization",
                required_modules=["memory", "synthesis"],
                execution_order=[
                    CognitiveStep(module_name="memory", order_index=1),
                    CognitiveStep(module_name="synthesis", order_index=2)
                ],
                budgets={"max_latency_ms": 1500}
            )

        # --- PHASE 0.3: Fresh Knowledge Route (WEB SEARCH) ---
        if detect_web_requirement(q_lower):
            print(f"[BRAIN] Fresh Knowledge Requirement detected. Routing to SEARCH_OPTIMIZED mode.")
            return CognitivePlan(
                pipeline_mode="direct",
                routing_reason="Fresh knowledge requirement",
                required_modules=["memory", "synthesis"], # Will trigger search in executor
                execution_order=[
                    CognitiveStep(module_name="memory", order_index=1),
                    CognitiveStep(module_name="synthesis", order_index=2)
                ],
                budgets={"max_latency_ms": 8000}
            )


        # --- PHASE 0.4: Deterministic Truth Injection (INSTANT) ---
        from apps.backend.reasoning.verifier import FACTUAL_TRUTH_GUARD
        q_norm = q_lower.strip(' .?!')
        if q_norm in FACTUAL_TRUTH_GUARD:
            print(f"[BRAIN] Deterministic Truth Injection matched: {q_norm}")
            return CognitivePlan(
                pipeline_mode="direct",
                routing_reason="Deterministic truth match",
                required_modules=["utility"],
                execution_order=[CognitiveStep(module_name="utility", order_index=1)],
                budgets={"max_latency_ms": 200}
            )

        # --- PHASE 0.5: Factual Risk Guard (High Confidence Facts) ---
        factual_keywords = ["cm", "pm", "chief minister", "prime minister", "president", "capital of", "who is", "who was"]
        if any(kw in q_lower for kw in factual_keywords):
            print(f"[BRAIN] Factual Query detected. Forcing VERIFIER path.")
            return CognitivePlan(
                pipeline_mode="direct",
                routing_reason="Factual risk guard activation",
                required_modules=["memory", "reasoning", "verifier"],
                execution_order=[
                    CognitiveStep(module_name="memory", order_index=1),
                    CognitiveStep(module_name="reasoning", order_index=2),
                    CognitiveStep(module_name="verifier", order_index=3)
                ],
                budgets={"max_latency_ms": 6000}
            )

        # --- PHASE 1: Smart Fast-Path Router (Deterministic Heuristics) ---
        fast_path_plan = self._get_fast_path_plan(q_lower)
        if fast_path_plan:
            latency_ms = (time.time() - start_time) * 1000
            fast_path_plan.routing_reason = "Fast-path heuristic match"
            print(f"[BRAIN][OPTIMIZED] Fast-path routing active. Decision Latency: {latency_ms:.1f}ms")
            return fast_path_plan

        # --- PHASE 2: Complexity Heuristics & Activation Thresholding ---
        complexity_score = self._calculate_complexity_score(q_lower)
        
        # CATEGORY A: DIRECT_SIMPLE_RESPONSE (< 0.35)
        # For: factual definitions, casual chat, acknowledgments
        if complexity_score < 0.35:
            print(f"[BRAIN] DIRECT_SIMPLE_RESPONSE selected (Complexity: {complexity_score})")
            return CognitivePlan(
                pipeline_mode="direct",
                routing_reason=f"Low-complexity direct synthesis ({complexity_score})",
                required_modules=["memory", "synthesis"],
                execution_order=[
                    CognitiveStep(module_name="memory", order_index=1),
                    CognitiveStep(module_name="synthesis", order_index=2)
                ],
                budgets={"max_latency_ms": 2000}
            )

        # CATEGORY B: DIRECT_REASONING (0.35 - 0.6)
        # For: simple explanations, multi-step logic
        elif complexity_score <= 0.6:
            print(f"[BRAIN] DIRECT_REASONING selected (Complexity: {complexity_score})")
            return CognitivePlan(
                pipeline_mode="direct",
                routing_reason=f"Medium-complexity reasoning trace ({complexity_score})",
                required_modules=["memory", "reasoning"],
                execution_order=[
                    CognitiveStep(module_name="memory", order_index=1),
                    CognitiveStep(module_name="reasoning", order_index=2)
                ],
                budgets={"max_latency_ms": 5000}
            )

        # --- PHASE 3: Dynamic LLM Planning (For high-complexity / ambiguous tasks) ---
        print(f"[BRAIN] Planning heavy pipeline (Complexity: {complexity_score})...")
        messages = [
            {"role": "system", "content": COGNITIVE_PLANNER_PROMPT},
            {"role": "user", "content": f"Query: {query}\nComplexity Score: {complexity_score}"}
        ]
        
        raw = run_llm_inference(messages, self.model)
        plan_json = safe_parse_json(raw, fallback={})
        plan_json["routing_reason"] = "LLM-based dynamic planning"
        
        # Category C Enforcement: AUTONOMOUS / MULTI_AGENT
        mode = plan_json.get("pipeline_mode", "direct")
        if mode == "direct":
             print("[BRAIN] DIRECT_REASONING selected (LLM-Planned)")
        else:
             print(f"[BRAIN] {mode.upper()} mode selected (LLM-Planned)")
        
        # Inject latency budget based on mode
        mode = plan_json.get("pipeline_mode", "direct")
        budgets = {
            "direct": 1500,
            "multi_agent": 3000,
            "autonomous": 5000
        }
        plan_json["budgets"] = {"max_latency_ms": budgets.get(mode, 10000)}

        if plan_json:
            try:
                # Normalization & Recovery
                if not plan_json.get("required_modules") and plan_json.get("execution_order"):
                    plan_json["required_modules"] = [s.get("module_name") for s in plan_json["execution_order"] if isinstance(s, dict)]
                
                if not plan_json.get("execution_order") and plan_json.get("required_modules"):
                    plan_json["execution_order"] = [{"module_name": m, "order_index": i+1} for i, m in enumerate(plan_json["required_modules"])]
                
                return CognitivePlan(**plan_json)
            except Exception as e:
                print(f"[BRAIN] Plan validation failed: {e}")

        return CognitivePlan(pipeline_mode="direct", required_modules=["reasoning"], execution_order=[CognitiveStep(module_name="reasoning", order_index=1)])

    def _get_fast_path_plan(self, query: str) -> Optional[CognitivePlan]:
        """Deterministic routing for trivial voice / chat queries."""
        # 1. Greetings & Presence Checks (Target: < 1.0s)
        casual_patterns = [
            r"^(hi|hello|hey|yo|morning|evening|greetings)(\s+tony)?",
            r"^can you (hear|see) me\??",
            r"^how are you\??",
            r"^who (are you|is tony)\??",
            r"^(thanks|thank you|ok|okay|cool|nice)\.?$",
            r"^test(ing)?(\s+voice)?$",
        ]
        if any(re.search(p, query) for p in casual_patterns):
            return CognitivePlan(
                pipeline_mode="direct",
                routing_reason="Fast-path presence heuristic",
                required_modules=["memory", "synthesis"],
                execution_order=[
                    CognitiveStep(module_name="memory", order_index=1),
                    CognitiveStep(module_name="synthesis", order_index=2)
                ],
                budgets={"max_latency_ms": 1500}
            )

        # 2. Simple Factual Hooks (Target: < 2.0s)
        if query.startswith(("what time", "what day", "what date", "what is your")):
             return CognitivePlan(
                pipeline_mode="direct",
                routing_reason="Factual fast-path hook",
                required_modules=["memory", "synthesis"],
                execution_order=[
                    CognitiveStep(module_name="memory", order_index=1),
                    CognitiveStep(module_name="synthesis", order_index=2)
                ],
                budgets={"max_latency_ms": 2000}
            )

        # 3. Deterministic Tool Commands (Target: < 3.0s)
        # Bypasses: planner, world_model, reasoning, verifier
        if any(w in query for w in ["open", "search", "search for"]) and len(query.split()) < 10:
             return CognitivePlan(
                pipeline_mode="autonomous",
                routing_reason="Deterministic command bypass",
                required_modules=["autonomous_loop"],
                execution_order=[
                    CognitiveStep(module_name="autonomous_loop", order_index=1)
                ],
                budgets={"max_latency_ms": 3000}
            )
        return None

    def _calculate_complexity_score(self, query: str) -> float:
        """Heuristic analysis of task difficulty."""
        score = 0.0
        # Multi-step indicators
        if any(w in query for w in ["then", "and", "next", "after"]): score += 0.2
        # Ambiguity / Depth indicators
        if any(w in query for w in ["why", "how", "explain", "compare", "analyze"]): score += 0.3
        # Tool / World interaction indicators
        if any(w in query for w in ["open", "search", "find", "check", "run", "browse"]): score += 0.4
        # Multi-entity focus
        if len(query.split()) > 15: score += 0.2
        return min(score, 1.0)

    def _execute_module(self, mod_name: str, query: str, context: dict, plan: CognitivePlan, context_keys: List[str] = None) -> Dict[str, Any]:
        # 1. Check Cache
        keys_for_sum = sorted(context_keys) if context_keys is not None else sorted(list(context.keys()))
        input_data = {"query": query, "context_keys": keys_for_sum}
        cached = GLOBAL_COGNITION_CACHE.get(mod_name, input_data)
        if cached:
            return {"exchange": CognitiveExchange(**cached), "timing": 0.0, "hit": True}
        
        start_mod = time.time()
        output = None
        metadata = {}

        # --- REAL SUBSYSTEM DISPATCH ---
        if mod_name == "utility":
            # DETERMINISTIC UTILITY ROUTING
            social = resolve_social_query(query)
            q_norm = query.lower().strip(' .?!')
            from apps.backend.reasoning.verifier import FACTUAL_TRUTH_GUARD

            if social:
                 output = social
            elif q_norm in FACTUAL_TRUTH_GUARD:
                 output = f"The {q_norm} is {FACTUAL_TRUTH_GUARD[q_norm]}."
            elif plan.routing_reason.startswith("Semantic utility match: identity_profile"):
                 output = resolve_identity_query(query)
            else:
                 output = resolve_temporal_query(query)
        elif mod_name == "memory":
            output = fuse_with_memory_retrieval([], [])
        elif mod_name == "synthesis":
            # FAST-PATH DIRECT SYNTHESIS
            output = generate_direct_response(query, context, self.model)
        elif mod_name == "reasoning":
            output = generate_reasoned_response(query, context, self.model)
        elif mod_name == "multi_agent":
            output = run_multi_agent_workflow(query, self.model)
        elif mod_name == "autonomous_loop":
            output = run_autonomous_task(query, None, notification_service=None)
        elif mod_name == "world_model":
            output = simulate_candidate_action("initial", query, context, self.model)
        elif mod_name == "graph":
            output = traverse_related_entities(None, query, max_hops=1)
        elif mod_name == "verifier":
            prev_result = context.get("prev_output", "")
            output = verify_and_improve_answer(query, None, str(prev_result), self.model)
        
        exchange = CognitiveExchange(
            source_module=mod_name,
            payload=output,
            metadata=metadata
        )
        
        # 2. Update Cache
        GLOBAL_COGNITION_CACHE.set(mod_name, {"query": query, "context_keys": list(context.keys())}, exchange.model_dump())
        
        timing = (time.time() - start_mod) * 1000
        return {"exchange": exchange, "timing": timing, "hit": False}

    def run_cognitive_pipeline(self, query: str, context: dict, pre_computed_plan: Optional[CognitivePlan] = None) -> CognitiveTrace:
        start_brain = time.time()
        session_id = context.get("session_id", "default_session")
        db = context.get("db")

        # --- PHASE -1: STRICT MODEL ROUTING ---
        # Resolve model early so it's consistent across ALL steps
        detected_act = classify_dialogue_act(query)
        self.model = select_model(query, db=db, complexity=self._calculate_complexity_score(query), act=detected_act)
        print(f"[BRAIN] Model Router selected: {self.model}")

        # --- PHASE 0: CONTEXTUAL RESOLUTION & AMBIGUITY CHECK ---
        resolved_query, is_ambiguous, clarification = resolve_contextual_query(query, session_id, self.model)
        
        if is_ambiguous:
            print(f"[CONTEXT] Clarification Required: '{clarification}'")
            # Return immediate clarification plan
            dummy_plan = CognitivePlan(
                pipeline_mode="direct",
                routing_reason="Contextual ambiguity clarification",
                required_modules=["synthesis"],
                execution_order=[CognitiveStep(module_name="synthesis", order_index=1)]
            )
            trace = CognitiveTrace(plan=dummy_plan, final_result=clarification)
            return trace

        # Proceed with Resolved Query
        working_query = resolved_query
        
        print(f"[PIPELINE] Raw Query: {query}")
        print(f"[PIPELINE] Resolved Query: {working_query}")
        
        # Use provided plan or generate a new one
        if pre_computed_plan:
             plan = pre_computed_plan
        else:
             plan = self._generate_plan(working_query, context, detected_act)
              
        trace = CognitiveTrace(plan=plan, resolved_query=working_query)
        
        print(f"[BRAIN] Mode: {plan.pipeline_mode.upper()}")
        print(f"[BRAIN] Route Reason: {plan.routing_reason}")
        
        # --- HARD GUARDS & AUDIT LOGGING ---
        all_possible_modules = ["memory", "graph", "world_model", "reasoning", "synthesis", "multi_agent", "autonomous_loop", "verifier"]
        planned_modules = set(step.module_name for step in plan.execution_order)
        skipped_modules = [m for m in all_possible_modules if m not in planned_modules]
        
        print(f"[BRAIN] Audit: Executing {list(planned_modules)}")
        print(f"[BRAIN] Audit: Skipping {skipped_modules} (Bypass Logic Active)")
        sys.stdout.flush()
        
        active_context = context.copy()
        
        # Identify Parallelizable Context Modules (Group 1: Order Index <= 1)
        parallel_candidates = [s for s in plan.execution_order if s.order_index <= 1]
        sequential_steps = [s for s in plan.execution_order if s.order_index > 1]
        
        if len(parallel_candidates) > 1:
            print(f"[BRAIN] Parallelizing {len(parallel_candidates)} context modules...")
            start_p = time.time()
            stable_keys = list(active_context.keys())
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(parallel_candidates)) as executor:
                futures = {executor.submit(self._execute_module, s.module_name, working_query, active_context, plan, stable_keys): s for s in parallel_candidates}
                for future in concurrent.futures.as_completed(futures):
                    step = futures[future]
                    res_data = future.result()
                    
                    trace.module_outputs[step.module_name] = res_data["exchange"]
                    trace.execution_timings[step.module_name] = res_data["timing"]
                    if res_data["hit"]: trace.cache_stats["hits"] += 1
                    else: trace.cache_stats["misses"] += 1
                    
                    print(f"  [STAGE] {step.module_name.ljust(12)} | {res_data['timing']:>7.1f}ms")
                    
                    if step.module_name in ["memory", "graph"]:
                        active_context[f"{step.module_name}_context"] = res_data["exchange"].payload
            
            trace.parallel_speedup_ms = (sum(trace.execution_timings.values()) - (time.time() - start_p)*1000)
        else:
            for s in parallel_candidates:
                res_data = self._execute_module(s.module_name, working_query, active_context, plan)
                trace.module_outputs[s.module_name] = res_data["exchange"]
                trace.execution_timings[s.module_name] = res_data["timing"]
                if res_data["hit"]: trace.cache_stats["hits"] += 1
                else: trace.cache_stats["misses"] += 1
                
                print(f"  [STAGE] {s.module_name.ljust(12)} | {res_data['timing']:>7.1f}ms")

                if s.module_name in ["memory", "graph"]:
                    active_context[f"{s.module_name}_context"] = res_data["exchange"].payload

        # Execute Sequential Logic (Group 2: Order Index > 1)
        for step in sorted(sequential_steps, key=lambda x: x.order_index):
            elapsed = (time.time() - start_brain) * 1000
            
            # LATENCY BUDGET ENFORCEMENT
            limit = plan.budgets.get("max_latency_ms", 30000)
            if elapsed > limit:
                 print(f"  [STAGE] {step.module_name.ljust(12)} | ABORTED (Budget overflow: {elapsed:.0f}ms > {limit}ms)")
                 trace.skipped_modules.append({"module_name": step.module_name, "reason": "budget_overflow"})
                 continue

            if step.module_name == "verifier":
                 prev_mod = "multi_agent" if "multi_agent" in trace.module_outputs else "reasoning"
                 if prev_mod in trace.module_outputs:
                     active_context["prev_output"] = trace.module_outputs[prev_mod].payload

            res_data = self._execute_module(step.module_name, working_query, active_context, plan)
            trace.module_outputs[step.module_name] = res_data["exchange"]
            trace.execution_timings[step.module_name] = res_data["timing"]
            if res_data["hit"]: trace.cache_stats["hits"] += 1
            else: trace.cache_stats["misses"] += 1
            
            print(f"  [STAGE] {step.module_name.ljust(12)} | {res_data['timing']:>7.1f}ms")
            
        # Final Synthesis Selection
        pref_order = ["utility", "autonomous_loop", "multi_agent", "reasoning", "synthesis", "memory"]
        final_payload = "No result"
        for mod in pref_order:
            if mod in trace.module_outputs:
                payload = trace.module_outputs[mod].payload
                if mod == "reasoning" and isinstance(payload, tuple):
                    final_payload = payload[0]
                elif mod == "multi_agent" and isinstance(payload, dict):
                    final_payload = payload.get("final_output", payload)
                else:
                    final_payload = payload
                break

        # 3. Post-Process & Finalize
        sanitized = sanitize_response(final_payload)
        
        # --- RESPONSE SANITY CHECK ---
        # Ensure response reflects the working query context. Reject if completely unrelated.
        if not self._is_response_sane(working_query, sanitized):
            print(f"[BRAIN][WARN] Sanity check failed for response. Forcing grounded regeneration.")
            sanitized = "I'm sorry, I seem to have lost the thread of our conversation. Could you please rephrase that?"

        trace.final_result = sanitized
        trace.total_latency_ms = (time.time() - start_brain) * 1000
        
        current_topics, primary_topic = self._extract_topics(query, trace.final_result, session_id, detected_act)

        
        # 4. UPDATE CONTEXT FOR MULTI-TURN
        update_session_context(session_id, {
            "last_user_query": query, 
            "last_tony_response": trace.final_result,
            "active_topics": current_topics,
            "primary_topic": primary_topic,
            "last_dialogue_act": detected_act
        })
        
        print(f"[BRAIN] Dialogue State: Act={detected_act}, Topics={current_topics}, Primary='{primary_topic}'")
        print(f"[BRAIN] Total Pipeline Latency: {trace.total_latency_ms:.1f}ms")
        sys.stdout.flush()
        
        return trace

    def _is_response_sane(self, query: str, response: str) -> bool:
        """Heuristic check to ensure response isn't a hallucination or unrelated leakage."""
        q = query.lower()
        r = response.lower()
        
        # 1. Identity Lock Protection: If query is about identity/name, check response contains persona words
        if "who are you" in q or "your name" in q or "who made you" in q:
            persona_words = ["tony", "assistant", "ai", "creator", "designed", "help"]
            if not any(w in r for w in persona_words):
                 return False
                 
        # 2. Topic Grounding: If query contains specific entities, check response has some semantic overlap
        # (Very loose check for now)
        q_words = [w for w in q.split() if len(w) > 4]
        if q_words and len(r.split()) > 10:
             overlap = [w for w in q_words if w in r]
             if not overlap and "explain" not in q and "tell me more" not in q:
                  # For direct questions with entities, we expect some overlap
                  # return False # Disabled for now to prevent over-rejection
                  pass
                  
        return True

    def _extract_topics(self, query: str, response: str, session_id: str = "default", act: str = "QUESTION") -> Tuple[List[str], str]:
        """Extracts multiple semantic entities and a primary topic."""
        state = get_session_context(session_id)
        q_low = query.lower().strip().strip('?!.')
        
        # Subject Change Detection Guard
        social_words = {"hello", "hi", "hey", "thanks", "thank", "you", "morning", "evening", "afternoon", "bye", "goodbye", "ok", "okay"}
        generic_words = {
            "detail", "information", "thing", "everything", "it", "that", "this", "something", "more", "now", 
            "what", "is", "of", "the", "a", "an", "how", "who", "tell", "me", "about", "give", "example", 
            "both", "them", "those", "the two", "compare", "summarize", "show", "for", "in", "and", "or"
        }

        
        if q_low in social_words or q_low in generic_words or act in ["ACKNOWLEDGEMENT", "CHITCHAT", "AFFIRMATION"]:
             print(f"[CONTEXT] Preserve Topics: {state.active_topics}")
             return state.active_topics, state.primary_topic

        # Abbreviation Expansion
        abbreviations = {"ml": "machine learning", "ai": "artificial intelligence", "nlp": "natural language processing", "llm": "large language model"}
        for abbr, full in abbreviations.items():
            q_low = re.sub(rf'\b{abbr}\b', full, q_low)

        # Multi-Entity Extraction
        entities = []
        technical_keywords = ["python", "machine learning", "artificial intelligence", "deep learning", "neural network", "database", "api", "software", "hardware"]
        
        # Identify major entities via keyword and 'and' splits
        parts = re.split(r'\s+and\s+|,\s*', q_low)
        for part in parts:
            clean_part = part.strip()
            # Filter words
            words = [w for w in clean_part.split() if w not in generic_words]
            if words:
                entities.append(" ".join(words))

        # Deduplicate and limit
        entities = list(dict.fromkeys(entities))[:3]
        
        if not entities:
             return state.active_topics, state.primary_topic
        
        primary = entities[0]
        return entities, primary


def get_brain_controller(model: str = "phi3") -> CognitiveController:
    return CognitiveController(model)

def run_tony(query: str, context: Optional[dict] = None, model: str = "phi3") -> CognitiveTrace:
    """The unified master entry point for all Tony cognition."""
    current_context = context or {}
    brain = get_brain_controller(model)
    return brain.run_cognitive_pipeline(query, current_context)
