import time
import uuid
import re
from typing import Generator, Dict, Any, Optional
from apps.backend.schemas.streaming import StreamEvent
from apps.backend.cognition.cognitive_controller import get_brain_controller
from apps.backend.conversation.context_manager import get_session_context
from apps.backend.llm.inference import run_llm_inference, run_llm_inference_stream
from apps.backend.voice_ux.voice_ux_orchestrator import GLOBAL_VOICE_UX_ORCHESTRATOR

# active_streams maps stream_id -> cancellation_flag
active_streams: Dict[str, bool] = {}

def cancel_stream(stream_id: str):
    """Marks a stream for cancellation."""
    if stream_id in active_streams:
        active_streams[stream_id] = True
        print(f"[STREAM] Cancellation flag set for {stream_id}")

def stream_tony_response(query: str, context: Optional[dict] = None) -> Generator[StreamEvent, None, None]:
    """
    Main entry point for streaming. 
    Eliminates double-generation for fast-path / conversational results.
    """
    from apps.backend.llm.inference import get_llm_call_count, reset_llm_call_count
    reset_llm_call_count()
    
    query = re.sub(r'(\b\w+\b)(?:[!\?\s,]+\1\b)+', r'\1', query, flags=re.IGNORECASE)
    
    stream_id = str(uuid.uuid4())
    active_streams[stream_id] = False
    context = context or {}
    is_voice = context.get("interface") == "voice" or context.get("mode") == "production_fixed"

    # 1. Initialize Brain & Cognitive Plan
    brain = get_brain_controller()
    print(f"[STREAM] Starting cognitive pipeline for stream {stream_id}")
    
    # We yield a metadata event first with the cognitive plan
    plan = brain._generate_plan(query, context)
    yield StreamEvent(event_type="meta", content={"stream_id": stream_id, "plan": plan.model_dump()}, sequence_index=0)
    
    # 2. Run background cognitive steps
    start_time = time.time()
    trace = brain.run_cognitive_pipeline(query, context, pre_computed_plan=plan)
    elapsed_brain_ms = (time.time() - start_time) * 1000
    
    # LATENCY MASKING: If brain took > 500ms, yield filler
    if is_voice:
        filler = GLOBAL_VOICE_UX_ORCHESTRATOR.maybe_emit_latency_mask(elapsed_brain_ms)
        if filler:
            yield StreamEvent(event_type="token", content=filler + " ", sequence_index=-1)

    yield StreamEvent(event_type="meta", content={"trace_steps": list(trace.module_outputs.keys()), "brain_latency_ms": elapsed_brain_ms}, sequence_index=1)
    
    seq = 2
    # 3. Decision: Do we need a final synthesis?
    # If the brain already produced a conversational result (synthesis/reasoning), skip secondary LLM call.
    if trace.final_result and trace.final_result != "No result" and plan.pipeline_mode in ["direct", "multi_agent"]:
        print(f"[STREAM] {stream_id} using pre-generated result (Bypass Synthesis). Result Length: {len(str(trace.final_result))}")
        final_text = str(trace.final_result)
    else:
        # Standard fallback for autonomous / failed paths
        print(f"[STREAM] {stream_id} performing final synthesis...")
        voice_guidelines = ""
        if is_voice:
            voice_guidelines = """VOICE MODE ACTIVE: Be extremely concise (1-2 sentences). Use contractions. No markdown."""

        state = get_session_context(context.get("session_id", "default_session"))
        messages = [
            {"role": "system", "content": f"You are Tony, a sophisticated AI assistant. {voice_guidelines}"},
            {"role": "user", "content": f"Query: {trace.resolved_query or query}\n\nDialogue Context: {state.last_tony_response}\n\nFindings: {json_serialize_outputs(trace.module_outputs)}"}
        ]
        final_text = run_llm_inference(messages, brain.model)

    # 4. Optional UX Polishing for Voice
    if is_voice:
        optimized_res = GLOBAL_VOICE_UX_ORCHESTRATOR.optimize_voice_response(
            trace.resolved_query or query, final_text, trace, elapsed_brain_ms
        )
        final_text = optimized_res.optimized_text
        if optimized_res.follow_up:
            final_text += " " + optimized_res.follow_up

    # 4b. Yield Final Transcript Metadata (For logging/UI before TTS starts)
    yield StreamEvent(event_type="transcript", content={
        "text": final_text,
        "mode": plan.pipeline_mode.upper(),
        "routing_reason": plan.routing_reason,
        "latency_ms": (time.time() - start_time) * 1000,
        "word_count": len(final_text.split()),
        "char_count": len(final_text)
    }, sequence_index=seq)
    seq += 1

    # 5. Token Streaming Loop
    for token in re.findall(r'\S+|\s+', final_text):
        if active_streams.get(stream_id): break
        yield StreamEvent(event_type="token", content=token, sequence_index=seq)
        seq += 1
        time.sleep(0.01) # Tiny delay for smooth UI arrival
        
    print(f"[STREAM] Total LLM Calls for this request: {get_llm_call_count()}")
    sys_flush()

    # 5. Cleanup
    if not active_streams.get(stream_id):
        trace.final_result = final_text.strip()
        yield StreamEvent(event_type="done", content={"final_result": trace.final_result, "trace": trace.model_dump()}, sequence_index=seq)
    
    if stream_id in active_streams:
        del active_streams[stream_id]

def sys_flush():
    import sys
    sys.stdout.flush()

def json_serialize_outputs(outputs: Dict[str, Any]) -> str:
    res = ""
    for mod, exchange in outputs.items():
        res += f"\n--- {mod.upper()} ---\n{str(exchange.payload)}\n"
    return res
