import sounddevice as sd
import numpy as np
import time

def test_stream_data(device, rate, channels):
    print(f"Testing Device {device}, Rate {rate}, Channels {channels}...")
    received_data = []
    
    def callback(indata, frames, time, status):
        if status:
            print(f"  Status: {status}")
        received_data.append(np.abs(indata).max())

    try:
        with sd.InputStream(device=device, samplerate=rate, channels=channels, dtype='float32', callback=callback):
            time.sleep(1.0)
        
        if len(received_data) == 0:
            print("  [FAIL] No callback invocations!")
        else:
            max_amp = max(received_data)
            print(f"  [OK] Received {len(received_data)} blocks. Max amplitude: {max_amp}")
            if max_amp == 0:
                print("  [WARN] Data is silent!")
    except Exception as e:
        print(f"  [CRITICAL] Stream failure: {e}")

if __name__ == "__main__":
    # From previous diag, Device 9 (WASAPI) and Device 5 (DirectSound) are candidates.
    # 9 is "Microphone Array" WASAPI.
    test_stream_data(9, 48000, 1)
    test_stream_data(9, 48000, 2)
