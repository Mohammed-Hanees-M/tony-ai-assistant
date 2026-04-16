import sounddevice as sd
import numpy as np

def test_api(api_name):
    print(f"\n--- Testing Host API: {api_name} ---")
    devices = sd.query_devices()
    hostapis = sd.query_hostapis()
    
    # Find api index
    api_idx = -1
    for i, h in enumerate(hostapis):
        if h['name'] == api_name:
            api_idx = i
            break
    
    if api_idx == -1:
        print(f"API {api_name} not found.")
        return

    # Find first input device for this API
    target_dev = -1
    for i, d in enumerate(devices):
        if d['hostapi'] == api_idx and d['max_input_channels'] > 0:
            target_dev = i
            print(f"Testing Device {i}: {d['name']}")
            break
    
    if target_dev == -1:
        print(f"No input devices for {api_name}")
        return

    rate = 48000
    channels = 2
    
    try:
        def callback(indata, frames, time, status):
            pass

        stream = sd.InputStream(device=target_dev, samplerate=rate, channels=channels, dtype='float32', callback=callback)
        print("  InputStream created.")
        stream.start()
        print("  [OK] Stream started successfully.")
        stream.stop()
        stream.close()
    except Exception as e:
        print(f"  [FAIL] {e}")

if __name__ == "__main__":
    test_api("Windows WASAPI")
    test_api("Windows DirectSound")
    test_api("MME")
