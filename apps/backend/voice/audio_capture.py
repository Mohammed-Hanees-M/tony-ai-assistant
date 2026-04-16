import sounddevice as sd
import numpy as np
import threading
import queue
import time
from typing import Generator, List, Optional
try:
    from scipy.signal import resample
except ImportError:
    resample = None

import sys

class AudioCapture:
    """
    Production-grade stabilized audio capture with automatic hardware negotiation.
    Ensures upstream modules (VAD/STT) receive requested 16kHz audio via internal resampling.
    """
    def __init__(self, sample_rate: int = 16000, chunk_size: int = 512):
        self.requested_sample_rate = sample_rate
        self.actual_sample_rate = sample_rate
        self.actual_channels = 1
        self.chunk_size = chunk_size
        self.gain = 2.0 # 2x Gain boost for laptop mics to improve VAD/STT
        self.audio_queue = queue.Queue()
        self.stream = None
        self.is_running = False
        self.selected_device_info = {}

    def _audio_callback(self, indata, frames, time, status):
        """Standard sounddevice callback."""
        if status:
            print(f"[AUDIO][WARN] Status: {status}")
            sys.stdout.flush()
            
        data = indata.copy()
        
        # 1. Downmix to Mono if multi-channel
        if self.actual_channels > 1:
            data = np.mean(data, axis=1, keepdims=True)
        
        # 2. Internal Resampling if hardware is at a different rate
        if self.actual_sample_rate != self.requested_sample_rate:
            if resample:
                num_samples = int(len(data) * self.requested_sample_rate / self.actual_sample_rate)
                data = resample(data, num_samples).astype(np.float32)
            else:
                # High-fidelity linear interpolation fallback
                x_old = np.linspace(0, 1, len(data))
                x_new = np.linspace(0, 1, int(len(data) * self.requested_sample_rate / self.actual_sample_rate))
                data = np.interp(x_new, x_old, data.flatten()).reshape(-1, 1).astype(np.float32)

        # 3. Apply Gain Boost
        if self.gain != 1.0:
            data = data * self.gain

        self.audio_queue.put(data)

    def start(self, device_index: Optional[int] = None):
        """
        Starts capture with production-grade multi-backend fallback.
        Includes mandatory delays between attempts to stabilize Intel SST drivers.
        """
        if self.is_running:
            return

        # Mandatory initial sleep to allow previous driver handles to clear
        time.sleep(0.3)

        # 1. Gather Candidate Devices & Parameters
        # We look for all instances of the same hardware across different APIs
        candidates = self._get_discovery_candidates(device_index)
        
        if not candidates:
            print("[AUDIO][CRITICAL] No valid input devices found.")
            sys.stdout.flush()
            return

        success = False
        last_error = ""

        print(f"[AUDIO] Attempting hardware initialization across {len(candidates)} configurations...")
        
        for cand in candidates:
            cand_idx = cand['index']
            cand_name = cand['name']
            cand_api = cand['api']
            cand_max_ch = cand['max_ch']
            cand_def_sr = cand['def_sr']

            # Define parameter combinations for this specific device
            test_rates = [int(cand_def_sr), self.requested_sample_rate, 44100, 48000]
            
            # Channel Priority Adjustment:
            # WASAPI often REQUIRES native channels.
            # DirectSound/MME are better at emulated Mono/Stereo.
            if cand_api == "Windows WASAPI":
                test_channels = [cand_max_ch]
                if 2 not in test_channels and cand_max_ch >= 2: test_channels.append(2)
                if 1 not in test_channels: test_channels.append(1)
            else:
                # DirectSound/MME: Prefer mono/stereo to avoid empty high-index channels
                test_channels = [1, 2]
                if cand_max_ch not in test_channels: test_channels.append(cand_max_ch)

            for rate in test_rates:
                for ch in test_channels:
                    # Delay before every distinct attempt to prevent handle exhaustion
                    time.sleep(0.2)
                    try:
                        # Attempt to open AND start to validate the host handle
                        self._try_open_stream(cand_idx, rate, ch)
                        self.stream.start()
                        
                        self.actual_sample_rate = rate
                        self.actual_channels = ch
                        self.selected_device_info = sd.query_devices(cand_idx)
                        
                        print(f"[AUDIO] === SUCCESSFUL CAPTURE START ===")
                        print(f"[AUDIO] Device: {cand_name}")
                        print(f"[AUDIO] API: {cand_api} (Index: {cand_idx})")
                        print(f"[AUDIO] Buffering: {ch}ch @ {rate}Hz")
                        
                        mode_str = "Native (Low-Latency)" if (rate == self.requested_sample_rate and ch == 1) else f"Downmix/Resample ({ch}ch@{rate}Hz -> 1ch@{self.requested_sample_rate}Hz)"
                        print(f"[AUDIO] Mode: {mode_str}")
                        sys.stdout.flush()
                        
                        self.is_running = True
                        success = True
                        break
                    except Exception as e:
                        last_error = str(e).split('\n')[0] # Brief error
                        # Clean up failed attempt immediately
                        if self.stream:
                            try:
                                self.stream.stop()
                                self.stream.close()
                            except: pass
                            self.stream = None
                        continue
                if success: break
            if success: break

        if not success:
            print(f"[AUDIO][CRITICAL] ALL capture attempts failed. Last error: {last_error}")
            sys.stdout.flush()
            raise RuntimeError(f"Could not initialize audio input: {last_error}")

    def _get_discovery_candidates(self, preferred_index: Optional[int]) -> List[dict]:
        """Returns a prioritized list of (device_index, api_name, capabilities)."""
        devices = sd.query_devices()
        apis = sd.query_hostapis()
        
        # Priority mapping for APIs
        api_priority = {
            "Windows WASAPI": 0,
            "Windows DirectSound": 1,
            "MME": 2
        }

        candidates = []
        for i, d in enumerate(devices):
            if d['max_input_channels'] > 0:
                api_name = apis[d['hostapi']]['name']
                rank = api_priority.get(api_name, 10)
                
                # Boost 'Microphone Array' devices within their API group
                name_penalty = 0 if "Microphone Array" in d['name'] else 0.5
                
                # If the user preferred a specific index, boost it significantly
                if preferred_index == i:
                    rank = -1
                else:
                    rank += name_penalty
                
                candidates.append({
                    "index": i,
                    "name": d['name'],
                    "api": api_name,
                    "rank": rank,
                    "max_ch": int(d['max_input_channels']),
                    "def_sr": d['default_samplerate']
                })
        
        # Sort by rank
        candidates.sort(key=lambda x: x['rank'])
        return candidates

    def _try_open_stream(self, device_index, rate, channels):
        """Opens InputStream with explicit blocksize and latency to stabilize performance."""
        self.stream = sd.InputStream(
            device=device_index,
            channels=channels,
            samplerate=rate,
            blocksize=self.chunk_size, 
            dtype='float32',
            latency='low',
            callback=self._audio_callback
        )



    def stop(self):
        """Stops the mic capture."""
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        self.is_running = False
        print("[AUDIO] Capture stopped.")



    def stream_frames(self) -> Generator[np.ndarray, None, None]:
        """Yields audio chunks as they arrive."""
        while self.is_running or not self.audio_queue.empty():
            try:
                chunk = self.audio_queue.get(timeout=1.0)
                yield chunk
            except queue.Empty:
                continue

def list_audio_devices():
    """Returns list of available audio input devices with host API info."""
    devices = sd.query_devices()
    input_devices = []
    for i, d in enumerate(devices):
        if d['max_input_channels'] > 0:
            # Try to get host api name
            host_api = "Unknown"
            try:
                host_api = sd.query_hostapis(d['hostapi'])['name']
            except: pass
            
            input_devices.append({
                "index": i, 
                "name": d['name'], 
                "rate": d['default_samplerate'],
                "api": host_api
            })
    return input_devices

