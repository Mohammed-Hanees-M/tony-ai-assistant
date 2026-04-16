from apps.backend.voice.audio_player import StreamingAudioPlayer
import numpy as np
import time
import sys

def verify_playback():
    print("=== StreamingAudioPlayer Verification ===")
    # Initialize with standard TTS rate
    player = StreamingAudioPlayer(sample_rate=22050)
    
    try:
        # 1. Startup and Negotiation
        print("Starting Player (Fallback discovery loop)...")
        player.start()
        
        # 2. State Validation
        print(f"Negotiated Configuration:")
        print(f"  API: {player.stream.device if hasattr(player.stream, 'device') else 'N/A'}")
        print(f"  Requested SR: {player.requested_sample_rate} Hz")
        print(f"  Hardware SR: {player.actual_sample_rate} Hz")
        
        # 3. Queue Chunk
        print("\nQueuing 1 second of white noise...")
        duration = 1.0 # seconds
        noise = np.random.uniform(-0.1, 0.1, int(player.requested_sample_rate * duration)).astype(np.float32)
        player.add_chunk(noise, sequence_index=1)
        
        # 4. Playback and Buffer wait
        print("Waiting for playback buffer...")
        player.wait_for_buffer(timeout=1.0)
        
        print("Playing for 1.5 seconds...")
        time.sleep(1.5)
        
        # 5. Stats check
        stats = player.get_stats()
        print(f"\nPlayer Stats: {stats}")
        
        if stats['played'] > 0:
            print("[SUCCESS] Audio player successfully processed and played audio.")
        else:
            print("[FAIL] No chunks played.")
            
    except Exception as e:
        print(f"[ERROR] Playback verification failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nStopping player...")
        player.stop()

if __name__ == "__main__":
    verify_playback()
