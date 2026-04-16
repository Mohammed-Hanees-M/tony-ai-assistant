import os
import sys
import numpy as np
import time
import queue
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.voice.audio_player import StreamingAudioPlayer

def run_verification():
    print("=== TONY STREAMING AUDIO PLAYER AUDIT (HARDENED) ===\n")

    # 1. Initialize Player (with mocked sounddevice to avoid hardware locks)
    with patch("sounddevice.OutputStream") as mock_stream_class:
        mock_stream = MagicMock()
        mock_stream.active = False
        mock_stream_class.return_value = mock_stream
        
        print("[STEP 1] Verifying Singleton Enforcement")
        p1 = StreamingAudioPlayer(sample_rate=16000)
        p2 = StreamingAudioPlayer(sample_rate=16000)
        assert p1 is p2
        assert p1.instance_id == p2.instance_id
        print(f"  -> Singleton confirmed (Instance: {p1.instance_id})")

        p1.start()
        assert p1.is_active is True
        mock_stream.start.assert_called_once()
        print("  -> Stream started successfully.")

        # 2. Feeding Chunks & Duplicate Detection
        print("\n[STEP 2] Verifying Chunk Queueing & Duplicate Rejection")
        c1 = np.ones(100, dtype='float32') * 0.1
        c2 = np.ones(100, dtype='float32') * 0.2
        
        p1.add_chunk(c1, sequence_index=0)
        p1.add_chunk(c2, sequence_index=1)
        p1.add_chunk(c1, sequence_index=0) # DUPLICATE!
        
        stats = p1.get_stats()
        assert stats["enqueued"] == 2
        assert stats["duplicates_blocked"] == 1
        print(f"  -> Duplicate rejection verified. blocked={stats['duplicates_blocked']}")

        # 3. Simulate Callback consumption
        callback = mock_stream_class.call_args[1]['callback']
        outdata = np.zeros((150, 1), dtype='float32')
        
        print("\n[STEP 3] Verifying Callback Seamless Stitching")
        callback(outdata, 150, None, None)
        assert np.all(outdata[:100] == 0.1)
        assert np.all(outdata[100:] == 0.2)
        print("  -> Callback stitching verified.")

        # 4. Underflow Handling
        print("\n[STEP 4] Verifying Starvation Silence")
        p1.flush()
        outdata_silent = np.ones((50, 1), dtype='float32')
        callback(outdata_silent, 50, None, None)
        assert np.all(outdata_silent == 0.0)
        print("  -> Starvation produces silence.")

        # 5. Multiple Start Guards
        print("\n[STEP 5] Verifying Multiple Start Guards")
        mock_stream.active = True
        p1.start()
        # Should NOT call mock_stream_class or mock_stream.start again
        assert mock_stream_class.call_count == 1
        print("  -> Redundant start ignored correctly.")

        p1.stop()
        print("\n=== HARDENED PLAYER AUDIT SUCCESSFUL ===")


if __name__ == "__main__":
    run_verification()
