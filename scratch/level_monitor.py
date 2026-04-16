from apps.backend.voice.audio_capture import AudioCapture
import numpy as np
import time
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def monitor_audio():
    print("=== Tony Audio Level Monitor ===")
    capturer = AudioCapture(sample_rate=16000)
    
    try:
        print("Starting AudioCapture (Hardware Selection Loop)...")
        capturer.start()
        
        print(f"\nMonitoring levels for 10 seconds. Speak into the mic!")
        print(f"Format: {capturer.actual_channels}ch @ {capturer.actual_sample_rate}Hz")
        
        start_time = time.time()
        chunk_count = 0
        max_seen = 0.0
        
        for frame in capturer.stream_frames():
            chunk_count += 1
            current_max = np.abs(frame).max()
            max_seen = max(max_seen, current_max)
            
            # Print level meter every 10 chunks (~0.3s)
            if chunk_count % 10 == 0:
                meter = "#" * int(current_max * 50)
                print(f"\rLevel: [{meter:<50}] Max: {max_seen:.6f}", end="")
                sys.stdout.flush()
                
            if time.time() - start_time > 10:
                break
        
        print(f"\n\nTotal chunks: {chunk_count}")
        print(f"Global Max Amplitude: {max_seen:.6f}")
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
    finally:
        capturer.stop()

if __name__ == "__main__":
    # Ensure PYTHONPATH or similar if needed, but we'll run from root
    monitor_audio()
