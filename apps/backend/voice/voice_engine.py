import time
import threading
from typing import Generator, Optional
from apps.backend.schemas.voice import VoiceTranscript, VoiceState, AudioChunk
from apps.backend.streaming.streaming_engine import stream_tony_response, cancel_stream

class VoiceEngine:
    VALID_TRANSITIONS = {
        "idle": ["listening", "thinking"],
        "listening": ["thinking", "idle"],
        "thinking": ["speaking", "interrupted", "idle", "error"],
        "speaking": ["idle", "interrupted", "error"],
        "interrupted": ["idle", "listening"],
        "error": ["idle"]
    }

    def __init__(self):
        self._states: dict[str, VoiceState] = {} # session_id -> VoiceState
        self._active_tts_streams: dict[str, bool] = {} # session_id -> interrupted_flag
        self._locks: dict[str, bool] = {} # session_id -> pipeline_active_lock
        self._thread_lock = threading.Lock()

    def set_state(self, session_id: str, status: str):
        if session_id not in self._states:
            self._states[session_id] = VoiceState(session_id=session_id, status="idle")
        
        current_status = self._states[session_id].status
        if status not in self.VALID_TRANSITIONS.get(current_status, []):
             print(f"[VOICE WARNING] Blocked invalid transition: {current_status} -> {status}")
             return False

        self._states[session_id].status = status
        self._states[session_id].last_state_change = time.time()
        print(f"[VOICE STATE] {session_id}: {current_status.upper()} -> {status.upper()}")
        return True

    def acquire_pipeline_lock(self, session_id: str) -> bool:
        with self._thread_lock:
            if self._locks.get(session_id):
                print(f"[VOICE] Duplicate invocation blocked for session {session_id}")
                return False
            self._locks[session_id] = True
            return True

    def release_pipeline_lock(self, session_id: str):
        with self._thread_lock:
            self._locks[session_id] = False

    def process_voice_input(self, audio: bytes, provider="mock") -> VoiceTranscript:
        """Simulates STT transcription."""
        # In a real system, this would call Whisper, Google STT, etc.
        if provider == "mock":
            return VoiceTranscript(text="This is a mock transcript from speech.", confidence=0.98)
        return VoiceTranscript(text="Transcription Error", confidence=0.0)

    def stream_voice_output(self, text_gen: Generator, session_id: str) -> Generator[AudioChunk, None, None]:
        """
        Takes a text generator (from StreamingEngine) and yields AudioChunks (TTS).
        Supports interruption and single-entry SPEAKING state.
        """
        self._active_tts_streams[session_id] = False
        
        # 1. ENTER SPEAKING ONCE
        if not self.set_state(session_id, "speaking"):
             # If transition fails (e.g. interrupted while thinking), abort
             return

        seq = 0
        try:
            for chunk in text_gen:
                if self._active_tts_streams.get(session_id):
                    self.set_state(session_id, "interrupted")
                    return # Exit generator
                
                audio_data = f"<AUDIO:{chunk}>".encode()
                yield AudioChunk(data=audio_data, sequence_index=seq)
                seq += 1
                
            if not self._active_tts_streams.get(session_id):
                yield AudioChunk(data=b"<DONE>", sequence_index=seq, is_final=True)
                # 2. EXIT TO IDLE ONLY AFTER COMPLETION
                self.set_state(session_id, "idle")
                
        except Exception as e:
            print(f"[VOICE] TTS Error: {e}")
            self.set_state(session_id, "error")
        finally:
            if session_id in self._active_tts_streams:
                del self._active_tts_streams[session_id]

    def get_clarification_transcript(self) -> VoiceTranscript:
        """Returns a system-injected transcript for clarification flow."""
        return VoiceTranscript(text="I'm sorry, I didn't catch that correctly. Could you please repeat yourself?", confidence=1.0)

    def interrupt(self, session_id: str):
        """Halts STT/TTS for the session."""
        if session_id in self._active_tts_streams:
            self._active_tts_streams[session_id] = True
            print(f"[VOICE] Interruption triggered for {session_id}")

GLOBAL_VOICE_ENGINE = VoiceEngine()
