import torch
import numpy as np
from typing import Optional, List, Tuple

class VADEngine:
    def __init__(self, sample_rate: int = 16000, threshold: float = 0.5, use_model: bool = True):
        self.sample_rate = sample_rate
        self.threshold = threshold
        
        # Load Silero VAD model
        self.model = None
        if use_model:
            try:
                self.model, self.utils = torch.hub.load(
                    repo_or_dir='snakers4/silero-vad',
                    model='silero_vad',
                    trust_repo=True, # Attempt to auto-trust
                    force_reload=False,
                    onnx=False
                )
                (self.get_speech_timestamps, _, _, _, _) = self.utils
                print("[VAD] Silero VAD loaded successfully.")
            except Exception as e:
                print(f"[VAD] Skipping Silero VAD load: {e}")

        self.speech_active = False
        self.utterance_buffer = [] # Cumulative audio frames for current utterance
        # We aim for ~650ms silence threshold before finalizing an utterance
        self.silence_timeout_ms = 650
        self.max_silence_frames = 25 # Initial guess, updated on first chunk
        self.silence_frames = 0

    def process_chunk(self, chunk: np.ndarray) -> Optional[np.ndarray]:
        """
        Processes a single audio chunk.
        Returns the full utterance if speech completion detected, otherwise None.
        """
        # Dynamic threshold update based on actual chunk size received
        ms_per_chunk = (len(chunk) / self.sample_rate) * 1000
        if ms_per_chunk > 0:
            self.max_silence_frames = int(self.silence_timeout_ms / ms_per_chunk)
        # 1. Unified Energy Calculation (Production fallback)
        # We calculate RMS energy for the chunk
        rms = np.sqrt(np.mean(chunk**2))
        
        if self.model:
            try:
                tensor_chunk = torch.from_numpy(chunk.squeeze())
                with torch.no_grad():
                    prob = self.model(tensor_chunk, self.sample_rate).item()
            except:
                prob = rms * 15 # Heuristic fallback
        else:
            prob = rms * 15 # Heuristic scale

        is_speech = prob > self.threshold

        if is_speech:
            if not self.speech_active:
                print(f"[VAD] Speech START detected (Prob: {prob:.2f})")
            self.speech_active = True
            self.silence_frames = 0
            self.utterance_buffer.append(chunk)
        else:
            if self.speech_active:
                self.silence_frames += 1
                self.utterance_buffer.append(chunk)
                
                if self.silence_frames >= self.max_silence_frames:
                    print(f"[VAD] Speech END detected. Finalizing {len(self.utterance_buffer)} chunks.")
                    
                    # HARDENED CONCATENATION: Ensure all chunks are flattened and same dtype
                    try:
                        # Flatten each chunk in case they are (N, 1) and concatenate
                        full_utterance = np.concatenate([c.flatten() for c in self.utterance_buffer]).astype(np.float32)
                        # Ensure contiguous for library compatibility
                        full_utterance = np.ascontiguousarray(full_utterance)
                        
                        duration_sec = len(full_utterance) / self.sample_rate
                        print(f"[VAD] Utterance Finalized: {duration_sec:.2f}s, Shape: {full_utterance.shape}, Dtype: {full_utterance.dtype}")
                        
                        self._reset()
                        return full_utterance
                    except Exception as e:
                        print(f"[VAD ERROR] Concatenation failed: {e}")
                        self._reset()
                        return None
        
        return None

    def _reset(self):
        self.speech_active = False
        self.utterance_buffer = []
        self.silence_frames = 0

    def is_triggered(self) -> bool:
        return self.speech_active
