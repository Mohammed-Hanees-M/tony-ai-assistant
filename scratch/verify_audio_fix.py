from apps.backend.voice.audio_capture import AudioCapture
import time
import sys

def verify_fix():
    print("=== Tony Audio Capture Verification ===")
    capturer = AudioCapture(sample_rate=16000)
    
    try:
        print("Starting AudioCapture...")
        capturer.start()
        
        print(f"Negotiated Configuration:")
        print(f"  Device: {capturer.selected_device_info.get('name')}")
        print(f"  Hardware Rate: {capturer.actual_sample_rate} Hz")
        print(f"  Hardware Channels: {capturer.actual_channels}")
        
        print("\nCapturing for 3 seconds...")
        frames_received = 0
        timeout = time.time() + 3
        
        for frame in capturer.stream_frames():
            frames_received += 1
            if time.time() > timeout:
                break
            
            # Print a progress indicator
            if frames_received % 10 == 0:
                print(".", end="")
                sys.stdout.flush()
        
        print(f"\nCaptured {frames_received} chunks.")
        
        if frames_received > 0:
            print("[SUCCESS] Audio capture pipeline is functional.")
        else:
            print("[FAIL] No audio frames received.")
            
    except Exception as e:
        print(f"[ERROR] Failed to run AudioCapture: {e}")
    finally:
        capturer.stop()

if __name__ == "__main__":
    verify_fix()
