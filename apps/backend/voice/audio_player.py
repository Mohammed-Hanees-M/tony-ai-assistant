import numpy as np
import sounddevice as sd
import queue
import threading
import time
import uuid
import sys
try:
    from scipy.signal import resample
except ImportError:
    resample = None
from typing import Optional

class StreamingAudioPlayer:
    """
    Production-grade streaming audio player using sounddevice OutputStream.
    Hardened with strict singleton enforcement and deep telemetry.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(StreamingAudioPlayer, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, sample_rate=22050, channels=1):
        if self._initialized:
            return
            
        self.instance_id = str(uuid.uuid4())[:8]
        self.requested_sample_rate = sample_rate # The rate of incoming audio (e.g. TTS 22k)
        self.actual_sample_rate = sample_rate    # The rate of the hardware (e.g. 48k)
        self.channels = channels
        self.audio_queue = queue.Queue()
        self.is_active = False
        self.stream = None
        
        # Playback State
        self.current_chunk = None
        self.current_chunk_ptr = 0
        self.last_queued_seq = -1
        
        # Instrumentation
        self.total_chunks_enqueued = 0
        self.total_chunks_played = 0
        self.total_frames_rendered = 0
        self.callback_count = 0
        self.duplicate_chunk_events = 0
        
        # Buffer-ahead logic
        self.min_buffer_seconds = 0.4
        
        self._initialized = True
        print(f"[PLAYER][{self.instance_id}] Singleton initialized. SR={sample_rate}, Device={sd.default.device}")

    def _callback(self, outdata, frames, time_info, status):
        """Callback for sounddevice OutputStream."""
        self.callback_count += 1
        if status:
            print(f"[PLAYER][{self.instance_id}][STATUS] {status}")
            
        filled = 0
        while filled < frames:
            if self.current_chunk is None:
                try:
                    # Non-blocking get from queue
                    self.current_chunk = self.audio_queue.get_nowait()
                    self.current_chunk_ptr = 0
                    self.total_chunks_played += 1
                except queue.Empty:
                    # STARVATION: If no audio, fill with silence
                    outdata[filled:] = 0
                    break
            
            # Fill outdata from current chunk
            remaining_in_chunk = len(self.current_chunk) - self.current_chunk_ptr
            needed = frames - filled
            to_copy = min(remaining_in_chunk, needed)
            
            # Reshape for sounddevice (frames, channels)
            chunk_view = self.current_chunk[self.current_chunk_ptr : self.current_chunk_ptr + to_copy]
            outdata[filled:filled + to_copy] = chunk_view.reshape(-1, self.channels)
            
            filled += to_copy
            self.current_chunk_ptr += to_copy
            self.total_frames_rendered += to_copy
            
            if self.current_chunk_ptr >= len(self.current_chunk):
                self.current_chunk = None

    def start(self, device_index: Optional[int] = None):
        """Initializes and starts a validated persistent output stream with fallback."""
        if self.stream is not None:
            if self.stream.active:
                return
            else:
                try: 
                    self.stream.start()
                    return
                except: pass # If restart fails, we'll recreate
        
        # Mandatory initial sleep to allow driver handles to clear
        time.sleep(0.3)

        # 1. Gather Candidate Devices
        candidates = self._get_discovery_candidates(device_index)
        
        success = False
        last_error = ""

        print(f"[PLAYER][{self.instance_id}] Attempting playback start across {len(candidates)} configurations...")

        for cand in candidates:
            cand_idx = cand['index']
            cand_name = cand['name']
            cand_api = cand['api']
            
            # Delay before every distinct attempt
            time.sleep(0.2)
            
            try:
                # ASSERTION: Ensure all required state is initialized
                assert hasattr(self, 'requested_sample_rate'), "requested_sample_rate not initialized"
                assert hasattr(self, 'actual_sample_rate'), "actual_sample_rate not initialized"
                assert hasattr(self, 'channels'), "channels not initialized"

                # Attempt to validate and start immediately
                # If requested SR fails, we try hardware default
                sr_to_try = [self.requested_sample_rate, int(cand['def_sr']), 44100, 48000]
                
                for sr in sr_to_try:
                    try:
                        self.stream = sd.OutputStream(
                            device=cand_idx,
                            samplerate=sr,
                            channels=self.channels,
                            callback=self._callback,
                            dtype='float32',
                            blocksize=1024, # Stabilize callback frequency
                            latency='low'
                        )
                        self.stream.start()
                        
                        self.actual_sample_rate = sr
                        print(f"[PLAYER][{self.instance_id}] === SUCCESSFUL PLAYBACK START ===")
                        print(f"[PLAYER] Device: {cand_name}")
                        print(f"[PLAYER] API: {cand_api} (Index: {cand_idx})")
                        print(f"[PLAYER] Hardware Rate: {sr}Hz")
                        
                        if sr != self.requested_sample_rate:
                            print(f"[PLAYER] Internal Resampling: {self.requested_sample_rate}Hz -> {sr}Hz")
                        
                        sys.stdout.flush()
                        
                        self.is_active = True
                        success = True
                        break
                    except:
                        if self.stream: self.stream.close()
                        continue
                if success: break
            except Exception as e:
                last_error = str(e)
                continue
        
        if not success:
            print(f"[PLAYER][{self.instance_id}][CRITICAL] ALL playback attempts failed. Last error: {last_error}")
            sys.stdout.flush()
            raise RuntimeError(f"Could not initialize audio output: {last_error}")

    def _get_discovery_candidates(self, preferred_index: Optional[int]) -> list:
        """Returns a prioritized list of output candidates."""
        devices = sd.query_devices()
        apis = sd.query_hostapis()
        
        priority = {
            "Windows WASAPI": 0,
            "Windows DirectSound": 1,
            "MME": 2
        }
        
        candidates = []
        for i, d in enumerate(devices):
            if d['max_output_channels'] > 0:
                api_name = apis[d['hostapi']]['name']
                rank = priority.get(api_name, 10)
                
                # Boost preferred speakers
                name_penalty = 0 if any(k in d['name'] for k in ["Headphones", "Speaker"]) else 0.5
                
                if preferred_index == i:
                    rank = -1
                else:
                    rank += name_penalty

                candidates.append({
                    "index": i,
                    "name": d['name'],
                    "api": api_name,
                    "rank": rank,
                    "def_sr": d['default_samplerate']
                })
        
        candidates.sort(key=lambda x: x['rank'])
        return candidates




    def stop(self):
        """Stops the output stream and flushes queue."""
        self.is_active = False
        if self.stream:
            print(f"[PLAYER][{self.instance_id}] Stopping stream.")
            self.stream.stop()
            self.stream.close()
            self.stream = None
        self.flush()

    def flush(self):
        """Flushes the audio queue and current buffer."""
        count = 0
        while not self.audio_queue.empty():
            try: 
                self.audio_queue.get_nowait()
                count += 1
            except queue.Empty: break
        
        if count > 0:
            print(f"[PLAYER][{self.instance_id}] Flushed {count} chunks.")
            
        self.current_chunk = None
        self.current_chunk_ptr = 0
        self.last_queued_seq = -1

    def add_chunk(self, data: np.ndarray, sequence_index: int = -1):
        """Adds a float32 normalized PCM chunk with automatic resampling if needed."""
        if sequence_index != -1 and sequence_index <= self.last_queued_seq:
            self.duplicate_chunk_events += 1
            print(f"[PLAYER][{self.instance_id}][CRITICAL] REJECTED DUPLICATE CHUNK (Seq {sequence_index} <= Last {self.last_queued_seq})")
            return

        processed_data = data
        
        # 1. Resampling
        if self.actual_sample_rate != self.requested_sample_rate:
            if resample:
                num_samples = int(len(data) * self.actual_sample_rate / self.requested_sample_rate)
                processed_data = resample(data, num_samples).astype(np.float32)
            else:
                # Linear interpolation fallback if scipy is missing
                x_old = np.linspace(0, 1, len(data))
                x_new = np.linspace(0, 1, int(len(data) * self.actual_sample_rate / self.requested_sample_rate))
                processed_data = np.interp(x_new, x_old, data).astype(np.float32)

        self.total_chunks_enqueued += 1
        if sequence_index != -1:
            self.last_queued_seq = sequence_index
            
        self.audio_queue.put(processed_data)
        
    def wait_for_buffer(self, timeout=2.0):
        """Wait until we have enough audio queued to start playback safely."""
        start_wait = time.time()
        needed_samples = int(self.actual_sample_rate * self.min_buffer_seconds)
        
        while time.time() - start_wait < timeout:
            total_samples = sum(len(c) for c in list(self.audio_queue.queue))
            if total_samples >= needed_samples:
                return True
            time.sleep(0.05)
        return False
    
    def get_stats(self):
        return {
            "instance_id": self.instance_id,
            "enqueued": self.total_chunks_enqueued,
            "played": self.total_chunks_played,
            "duplicates_blocked": self.duplicate_chunk_events,
            "frames": self.total_frames_rendered,
            "callbacks": self.callback_count,
            "queue_size": self.audio_queue.qsize(),
            "active": self.stream.active if self.stream else False
        }


