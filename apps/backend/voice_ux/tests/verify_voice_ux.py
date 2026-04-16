import os
import sys
import time
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from apps.backend.voice_ux.voice_ux_orchestrator import GLOBAL_VOICE_UX_ORCHESTRATOR
from apps.backend.voice_ux.latency_masker import GLOBAL_LATENCY_MASKER
from apps.backend.voice_ux.schemas import VoiceResponseMode

def run_verification():
    print("=== TONY PREMIUM VOICE UX ARCHITECTURE VERIFICATION ===\n")
    
    orchestrator = GLOBAL_VOICE_UX_ORCHESTRATOR

    # [TEST 1] Mode Classification
    print("[TEST 1] Deterministic Response Policy Router")
    cases = [
        ("What is the capital of France?", "The capital of France is Paris.", VoiceResponseMode.FACTUAL),
        ("Play some jazz music.", "Sure, playing some jazz for you.", VoiceResponseMode.COMMAND),
        ("How do black holes work?", "Black holes are regions of spacetime where gravity is so strong that nothing, including light, can escape...", VoiceResponseMode.EDUCATIONAL),
        ("I'm feeling really down today.", "I'm sorry to hear that. I'm here for you.", VoiceResponseMode.EMOTIONAL)
    ]
    for q, a, expected in cases:
        mode = orchestrator.optimize_voice_response(q, a, None).mode
        print(f"  -> Query: '{q}' | Mode: {mode}")
        assert mode == expected, f"Classification failed! Got {mode}, expected {expected}"
    print("  -> PASSED")

    # [TEST 2] Semantic Compression
    print("\n[TEST 2] Semantic Sentence-Aware Compression")
    long_a = "Tony is a sophisticated AI assistant. He was built to help users with complex tasks and multi-agent orchestration. He can also carry out autonomous loops and research. Is there anything else you need?"
    res = orchestrator.optimize_voice_response("Who are you?", long_a, None)
    print(f"  -> Original len: {len(long_a)} | Optimized len: {len(res.optimized_text)}")
    print(f"  -> Text: '{res.optimized_text}'")
    
    # 2 sentences max
    sentences = res.optimized_text.split(".")
    # Note: re.split in compressor might be more accurate but we do a quick check
    assert len([s for s in sentences if len(s.strip()) > 0]) <= 2, "Compression failed to limit sentences!"
    assert res.was_compressed is True
    print("  -> PASSED")

    # [TEST 3] Tone & Persona Optimization
    print("\n[TEST 3] Tone Smoothing & Persona Enforcement")
    raw_a = "Actually, I think it is important. I am Tony and it is a pleasure."
    res = orchestrator.optimize_voice_response("Hello", raw_a, None)
    print(f"  -> Raw: '{raw_a}'")
    print(f"  -> Optimized: '{res.optimized_text}'")
    
    # Contractions
    assert "i'm" in res.optimized_text.lower()
    assert "it's" in res.optimized_text.lower()
    # Persona (Confident substitution)
    assert "Actually" not in res.optimized_text
    assert "It looks like" in res.optimized_text
    print("  -> PASSED")

    # [TEST 4] Latency Masking Logic
    print("\n[TEST 4] Latency Masker Threshold & Cooldown")
    # A. Below threshold
    filler1 = orchestrator.maybe_emit_latency_mask(400)
    assert filler1 is None, "Filler emitted below 500ms threshold!"
    
    # B. Above threshold
    orchestrator.latency_masker = GLOBAL_LATENCY_MASKER # in case of reload
    GLOBAL_LATENCY_MASKER.state.last_filler_time = 0 # reset cooldown
    filler2 = orchestrator.maybe_emit_latency_mask(600)
    print(f"  -> Filler 600ms: '{filler2}'")
    assert filler2 is not None, "Filler NOT emitted above 500ms threshold!"
    
    # C. Cooldown enforcement
    filler3 = orchestrator.maybe_emit_latency_mask(700)
    assert filler3 is None, "Filler emitted despite 10s cooldown!"
    print("  -> PASSED")

    # [TEST 5] Follow-up Generation
    print("\n[TEST 5] Follow-up Prompt Logic")
    # Since it's randomized (20%), we force it or run multiple times
    found_follow_up = False
    with patch("random.random", return_value=0.1):
        res = orchestrator.optimize_voice_response("Fact", "Fact check result.", None)
        if res.follow_up:
            found_follow_up = True
            print(f"  -> Generated Follow-up: '{res.follow_up}'")
            
    assert found_follow_up, "Follow-up generation triggered but none found!"
    print("  -> PASSED")

    print("\n=== ARCHITECTURE VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    run_verification()
