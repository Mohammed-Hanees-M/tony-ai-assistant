from typing import Any, Optional
from apps.backend.voice_ux.schemas import OptimizedVoiceResponse, VoiceResponseMode
from apps.backend.voice_ux.response_policy import GLOBAL_POLICY_ROUTER
from apps.backend.voice_ux.compressor import GLOBAL_COMPRESSOR
from apps.backend.voice_ux.tone_optimizer import GLOBAL_TONE_OPTIMIZER
from apps.backend.voice_ux.persona_enforcer import GLOBAL_PERSONA_ENFORCER
from apps.backend.voice_ux.followup_generator import GLOBAL_FOLLOWUP_GENERATOR
from apps.backend.voice_ux.latency_masker import GLOBAL_LATENCY_MASKER

class VoiceUXOrchestrator:
    """Main pipeline orchestrator for premium voice response delivery."""
    
    def maybe_emit_latency_mask(self, elapsed_ms: float) -> Optional[str]:
        """Public proxy for latency masking logic."""
        return GLOBAL_LATENCY_MASKER.maybe_emit_latency_mask(elapsed_ms)

    def optimize_voice_response(
        self, 
        user_query: str, 
        assistant_output: str, 
        cognitive_trace: Any,
        elapsed_ms: float = 0.0
    ) -> OptimizedVoiceResponse:
        
        # 1. Classify (DETERMINISTIC)
        mode = GLOBAL_POLICY_ROUTER.classify_response_mode(user_query, assistant_output, cognitive_trace)
        
        # 2. Compress (SENTENCE-AWARE)
        compressed = GLOBAL_COMPRESSOR.compress_to_voice_friendly(assistant_output, mode)
        was_compressed = len(compressed) < len(assistant_output)
        
        # 3. Tone Optimization (spoken cadence)
        smooth_text = GLOBAL_TONE_OPTIMIZER.optimize_for_spoken_conversation(compressed)
        
        # 4. Persona Enforcement (Tony brand confidence)
        tony_text = GLOBAL_PERSONA_ENFORCER.enforce_tony_persona(smooth_text)
        
        # 5. Latency Masking (Conditional)
        filler = self.maybe_emit_latency_mask(elapsed_ms)
        
        # 6. Follow-up generation
        follow_up = GLOBAL_FOLLOWUP_GENERATOR.generate_followup_prompt(mode)
        
        return OptimizedVoiceResponse(
            original_text=assistant_output,
            optimized_text=tony_text,
            mode=mode,
            follow_up=follow_up,
            was_compressed=was_compressed
        )

GLOBAL_VOICE_UX_ORCHESTRATOR = VoiceUXOrchestrator()
