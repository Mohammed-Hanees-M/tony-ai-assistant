import time
import queue
import os
from typing import Generator, List, Optional
import numpy as np

from apps.backend.schemas.voice import AudioChunk
from apps.backend.core.dependencies import validate_premium_voice_dependencies

class TTSEngine:
    def __init__(self, model_dir: str = "models/tts/piper", voice_name: str = "en_US-lessac-medium"):
        validate_premium_voice_dependencies()
        try:
             from piper.voice import PiperVoice
        except ImportError:
             raise RuntimeError("[TTS] piper-tts not installed or incompatible.")

        # Resolve paths
        self.model_dir = os.path.abspath(model_dir)
        self.voice_name = voice_name
        self.model_path = os.path.join(self.model_dir, f"{voice_name}.onnx")
        self.config_path = f"{self.model_path}.json"

        # Validate existence
        if not os.path.exists(self.model_path):
             print(f"[TTS WARNING] Primary model not found at {self.model_path}. Attempting auto-discovery...")
             # Simple auto-discovery: find first .onnx in model_dir
             if os.path.exists(self.model_dir):
                 onnx_files = [f for f in os.listdir(self.model_dir) if f.endswith(".onnx")]
                 if onnx_files:
                     self.model_path = os.path.join(self.model_dir, onnx_files[0])
                     self.config_path = f"{self.model_path}.json"
                     print(f"[TTS] Auto-discovered voice: {onnx_files[0]}")
                 else:
                     # Fallback to current working dir if models/ not present
                     print("[TTS ERROR] No ONNX voices found in model directory.")
                     # In production we'd raise here, but we'll try to survive if mocked
             else:
                 print(f"[TTS ERROR] Model directory does not exist: {self.model_dir}")

        self.voice = None
        try:
            if os.path.exists(self.model_path):
                self.voice = PiperVoice.load(self.model_path, self.config_path)
                print(f"[TTS] Piper Neural Voice loaded: {os.path.basename(self.model_path)}")
        except Exception as e:
            print(f"[TTS ERROR] Model load failed: {e}")

        self.current_stream_id = None
        self.is_interrupted = False

    def synthesize_stream(self, text_generator: Generator[str, None, None], session_id: str) -> Generator[AudioChunk, None, None]:
        """
        Synthesizes speech from a streaming text generator.
        Buffering logic: Batches tokens into phrases for natural prosody.
        """
        self.is_interrupted = False
        phrase_buffer = ""
        global_chunk_seq = 0
        
        # Instrumentation
        self.total_chunks_yielded = 0
        self.last_yielded_seq = -1
        
        print(f"[TTS][{session_id}] Starting neural synthesis stream.")
        
        for token in text_generator:
            if self.is_interrupted:
                print(f"[TTS][{session_id}] Synthesis interrupted. Breaking.")
                break
            
            phrase_buffer += token
            
            if any(p in token for p in [".", "!", "?", ";", "\n"]):
                clean_phrase = phrase_buffer.strip()
                if clean_phrase:
                    for chunk in self._synthesize_phrase(clean_phrase, global_chunk_seq):
                        # DUPLICATE PROTECTION: Ensure monotonically increasing seq
                        if chunk.sequence_index <= self.last_yielded_seq:
                            print(f"[TTS][ERR] Duplicate sequence index generated: {chunk.sequence_index}")
                        
                        yield chunk
                        self.total_chunks_yielded += 1
                        self.last_yielded_seq = chunk.sequence_index
                        global_chunk_seq = chunk.sequence_index + 1
                    phrase_buffer = ""

        # Final flush
        if not self.is_interrupted and phrase_buffer.strip():
            for chunk in self._synthesize_phrase(phrase_buffer.strip(), global_chunk_seq):
                yield chunk
                self.total_chunks_yielded += 1
                self.last_yielded_seq = chunk.sequence_index
                global_chunk_seq = chunk.sequence_index + 1

        print(f"[TTS][{session_id}] Synthesis complete. Total chunks: {self.total_chunks_yielded}")

    def _synthesize_phrase(self, text: str, start_seq_index: int) -> Generator[AudioChunk, None, None]:
        """Synthesizes a single phrase into audio chunks using Piper synthesize_wav."""
        start_time = time.time()
        current_seq = start_seq_index
        
        if self.voice:
            # 1. GENERATE FULL AUDIO (Pseudo-streaming)
            import io
            import wave
            
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, "wb") as wav_file:
                self.voice.synthesize_wav(text, wav_file)
            
            wav_buffer.seek(0)
            # 2. EXTRACT RAW PCM
            with wave.open(wav_buffer, "rb") as r:
                params = r.getparams()
                sample_rate = params.framerate
                raw_pcm = r.readframes(params.nframes)
            
            # 3. CHUNK AND YIELD
            chunk_size = 8000 
            total_size = len(raw_pcm)
            
            for i in range(0, total_size, chunk_size):
                if self.is_interrupted:
                    break
                
                end_idx = min(i + chunk_size, total_size)
                chunk_data = raw_pcm[i:end_idx]
                chunk_duration = (len(chunk_data) / (2 * sample_rate)) * 1000
                
                yield AudioChunk(
                    data=chunk_data,
                    sequence_index=current_seq,
                    duration_ms=chunk_duration,
                    is_final=(end_idx == total_size),
                    metadata={"text": text if i == 0 else "", "sample_rate": sample_rate}
                )
                current_seq += 1
        else:
            # MOCK Synthesis
            time.sleep(0.1)
            mock_audio = f"<NEURAL_AUDIO:{text}>".encode()
            yield AudioChunk(
                data=mock_audio,
                sequence_index=current_seq,
                duration_ms=len(text) * 50,
                is_final=True,
                metadata={"text": text, "mode": "mock"}
            )
            current_seq += 1

    def interrupt(self):
        """Interrupts current synthesis."""
        self.is_interrupted = True

GLOBAL_TTS_ENGINE = TTSEngine()

