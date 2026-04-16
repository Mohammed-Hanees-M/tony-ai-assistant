import sounddevice as sd
import numpy as np
import sys

def test_config(device, rate, channels, dtype='float32'):
    try:
        sd.check_input_settings(device=device, samplerate=rate, channels=channels, dtype=dtype)
        print(f"  [OK] check_input_settings(rate={rate}, channels={channels}, dtype={dtype})")
        
        def callback(indata, frames, time, status):
            if status:
                print(f"    [CB] Status: {status}")

        with sd.InputStream(device=device, samplerate=rate, channels=channels, dtype=dtype, callback=callback):
            sd.sleep(500)
            print(f"  [OK] InputStream created and started for 500ms")
        return True
    except Exception as e:
        print(f"  [FAIL] rate={rate}, channels={channels}: {e}")
        return False

def diagnostic():
    print("=== SoundDevice Diagnostic ===")
    devices = sd.query_devices()
    print(f"Total devices: {len(devices)}")
    
    hostapis = sd.query_hostapis()
    print("\nHost APIs:")
    for i, api in enumerate(hostapis):
        print(f" {i}: {api['name']}")

    # Identify best device using Tony's logic
    priority = {"Windows WASAPI": 0, "Windows DirectSound": 1, "MME": 2}
    valid_inputs = []
    for i, d in enumerate(devices):
        if d['max_input_channels'] > 0:
            api_name = hostapis[d['hostapi']]['name']
            rank = priority.get(api_name, 10)
            valid_inputs.append((rank, i, d['name'], api_name, d))
    
    valid_inputs.sort(key=lambda x: x[0])
    
    if not valid_inputs:
        print("No input devices found!")
        return

    print("\nTop Candidate Devices (Tony's priority):")
    for rank, i, name, api, d in valid_inputs[:3]:
        print(f" Rank {rank} | Index {i} | {name} ({api}) | Max CH: {d['max_input_channels']} | Def SR: {d['default_samplerate']}")

    best_idx = valid_inputs[0][1]
    best_info = valid_inputs[0][4]
    print(f"\nTesting Best Candidate (Index {best_idx}):")
    
    rates_to_test = [16000, int(best_info['default_samplerate']), 44100, 48000, 48100]
    channels_to_test = [1, 2, int(best_info['max_input_channels'])]
    
    for r in rates_to_test:
        for c in channels_to_test:
            if c <= best_info['max_input_channels']:
                test_config(best_idx, r, c)

if __name__ == "__main__":
    diagnostic()
