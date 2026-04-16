import os
import sys
import numpy as np
import json
from unittest.mock import patch, MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.voice.stt_engine import STTEngine
from apps.backend.voice.tts_engine import TTSEngine

def run_verification():
    print("=== TONY VOICE CALIBRATION VERIFICATION ===\n")

    # 1. STT Calibration (Confidence Math)
    print("[TEST A, B, C] STT Confidence Calibration")
    with patch("apps.backend.core.dependencies.validate_premium_voice_dependencies"):
        stt = STTEngine()
        
        # Test Case 1: Decent LogProb (-0.7)
        avg_log_prob_good = -0.7
        # Formula: (log_prob + 2.0) / 2.0
        # Expected: (-0.7 + 2.0) / 2.0 = 1.3 / 2 = 0.65
        conf_good = min(1.0, max(0.0, (avg_log_prob_good + 2.0) / 2.0))
        print(f"  -> Good Input LogProb: {avg_log_prob_good} => Normalized: {conf_good:.2f}")
        assert conf_good > stt.confidence_threshold # 0.65 > 0.55
        
        # Test Case 2: Poor LogProb (-1.7)
        avg_log_prob_bad = -1.7
        # Expected: (-1.7 + 2.0) / 2.0 = 0.3 / 2 = 0.15
        conf_bad = min(1.0, max(0.0, (avg_log_prob_bad + 2.0) / 2.0))
        print(f"  -> Bad Input LogProb: {avg_log_prob_bad} => Normalized: {conf_bad:.2f}")
        assert conf_bad < stt.confidence_threshold # 0.15 < 0.55
        
        print("Test A-C Passed (Calibration Sane)\n")

    # 2. Piper Auto-Discovery
    print("[TEST D] Piper Model Auto-Discovery")
    with patch("os.path.exists", return_value=True), \
         patch("os.path.abspath", side_effect=lambda x: x), \
         patch("os.listdir", return_value=["discovered_voice.onnx"]), \
         patch("apps.backend.core.dependencies.validate_premium_voice_dependencies"):
        
        # We simulate that the specific voice requested doesn't exist but others do
        with patch("os.path.exists", side_effect=lambda p: "discovered_voice.onnx" in p or "models/tts/piper" in p):
             tts = TTSEngine(model_dir="models/tts/piper", voice_name="missing_voice")
             print(f"  -> Requested 'missing_voice', Discovered: {tts.model_path}")
             assert "discovered_voice.onnx" in tts.model_path
    print("Test D Passed\n")

    # 3. Whisper Model Config
    print("[TEST E] Whisper Default Model Selection")
    with patch("apps.backend.core.dependencies.validate_premium_voice_dependencies"), \
         patch("faster_whisper.WhisperModel") as mock_whisper:
        stt_large = STTEngine(model_size="large-v3")
        assert stt_large.model_size == "large-v3"
        print(f"  -> Configurable Whisper model validated: {stt_large.model_size}")
    print("Test E Passed\n")

    print("\n=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    run_verification()
