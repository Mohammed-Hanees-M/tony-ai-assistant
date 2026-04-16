import numpy as np
import time
import os
import scipy.io.wavfile as wav
from typing import Optional, Dict, Any, Tuple
from apps.backend.schemas.voice import VoiceTranscript
from apps.backend.core.dependencies import validate_premium_voice_dependencies

class STTEngine:
    def __init__(self, model_size: str = "small.en", device: str = "cpu", compute_type: str = "int8"):
        validate_premium_voice_dependencies()
        from faster_whisper import WhisperModel
        
        self.model_size = model_size
        self.confidence_threshold = 0.55 # Slightly relaxed from 0.65 to prevent over-rejection
        try:
            self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
            print(f"[STT] Faster-Whisper '{model_size}' loaded successfully.")
        except Exception as e:
            raise RuntimeError(f"[STT] Critical Failure: Could not load Whisper model: {e}")

    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000) -> VoiceTranscript:
        """Transcribes a raw audio buffer with hardened preprocessing and repair."""
        start_time = time.time()
        
        # 1. HARDENED REPAIR LOGIC
        # Ensure 1D (Mono)
        if audio_data.ndim > 1:
            audio_data = audio_data.flatten()
        
        # Ensure float32
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)
            
        # Ensure normalization [-1.0, 1.0]
        peak = np.max(np.abs(audio_data))
        if peak > 1.0:
            print(f"[STT] Normalizing audio (Peak: {peak:.2f})")
            audio_data = audio_data / peak
        elif peak < 0.05 and peak > 0:
            print(f"[STT] Boosting low volume audio (Peak: {peak:.2f})")
            audio_data = audio_data / (peak * 2) # Moderate boost
            
        # Ensure contiguous
        audio_data = np.ascontiguousarray(audio_data)

        # 2. AUDIO DIAGNOSTICS & EXPORT
        self._log_diagnostics(audio_data, sample_rate)
        self._export_debug_wav(audio_data, sample_rate)
        
        if self.model:
            # Transcribe via real Whisper
            segments, info = self.model.transcribe(audio_data, beam_size=5)
            
            text_segments = []
            log_probs = []
            
            for segment in segments:
                text_segments.append(segment.text)
                log_probs.append(segment.avg_logprob)
            
            final_text = "".join(text_segments).strip()
            
            # IMPROVED CONFIDENCE NORMALIZATION
            # avg_logprob: 0.0 is perfect, -1.0 is decent, -3.0 is very poor.
            # Linear mapping: 0.0 -> 1.0, -2.0 -> 0.0
            avg_log_prob = np.mean(log_probs) if log_probs else -10.0
            avg_conf = min(1.0, max(0.0, (avg_log_prob + 2.0) / 2.0))
            
            print(f"[STT] Whisper Engine: LogProb={avg_log_prob:.2f}, NormalizedConf={avg_conf:.2f}")
            language = info.language
        else:
            # MOCK implementation for verification
            time.sleep(0.5) # Simulate processing
            final_text = "Hello, I am testing Tony's premium voice pipeline."
            avg_conf = 0.95
            language = "en"

        duration_ms = (time.time() - start_time) * 1000
        
        # QUALITY FILTERS
        is_clarification = False
        if avg_conf < self.confidence_threshold or not final_text:
            is_clarification = True
            
        return VoiceTranscript(
            text=final_text,
            confidence=avg_conf,
            language=language,
            duration_ms=duration_ms,
            model_used=self.model_size,
            is_clarification_required=is_clarification,
            metadata={"segments_count": len(text_segments) if self.model else 1}
        )

    def _log_diagnostics(self, audio: np.ndarray, sr: int):
        rms = np.sqrt(np.mean(audio**2))
        peak = np.max(np.abs(audio))
        print(f"[STT DIAG] Dtype: {audio.dtype}, Shape: {audio.shape}, SR: {sr}Hz")
        print(f"[STT DIAG] Stats: Peak={peak:.4f}, RMS={rms:.4f}, Mean={np.mean(audio):.4f}")
        print(f"[STT DIAG] Sample Head: {audio[:10]}")

    def _export_debug_wav(self, audio: np.ndarray, sr: int):
        """Saves utterance to debug_wavs/ for manual audit."""
        try:
            debug_dir = "debug_wavs"
            if not os.path.exists(debug_dir):
                os.makedirs(debug_dir)
            
            timestamp = int(time.time())
            filename = os.path.join(debug_dir, f"utterance_{timestamp}.wav")
            # Convert back to int16 for standard WAV format compatibility
            int16_audio = (audio * 32767).astype(np.int16)
            wav.write(filename, sr, int16_audio)
            print(f"[STT DEBUG] Audio exported to {filename}")
        except Exception as e:
            print(f"[STT DEBUG] Export failed: {e}")

GLOBAL_STT_ENGINE = STTEngine()
