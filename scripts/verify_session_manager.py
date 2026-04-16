import os
import sys
import json
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.session.session_manager import create_session, get_session, close_session, link_stream_to_session, list_user_sessions
from apps.backend.session.session_repository import CACHE_FILE
from unittest.mock import patch

def run_verification():
    print("=== TONY SESSION MANAGER VERIFICATION (PART 9B) ===\n")
    
    # Cleanup
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)

    # 1. Creation & Resume
    print("[TEST A, B] Session Creation & Resume")
    sess1 = create_session("user_123", {"source": "mobile"})
    sid = sess1.session_id
    
    sess_resumed = get_session(sid)
    assert sess_resumed is not None
    assert sess_resumed.user_id == "user_123"
    assert sess_resumed.metadata["source"] == "mobile"
    print("Test A-B Passed\n")

    # 2. Stream Linking & Cancellation
    print("[TEST C, D] Stream Linking & Cancellation")
    stream_id = "test_stream_999"
    link_stream_to_session(sid, stream_id)
    
    updated_sess = get_session(sid)
    assert updated_sess.active_stream_id == stream_id
    
    with patch("apps.backend.session.session_manager.cancel_stream") as mock_cancel:
        close_session(sid)
        mock_cancel.assert_called_once_with(stream_id)
    
    final_sess = get_session(sid)
    assert final_sess.status == "closed"
    assert final_sess.active_stream_id is None
    print("Test C-D Passed\n")

    # 3. Multi-Session Isolation
    print("[TEST F] Multi-Session / User Isolation")
    sess2 = create_session("user_456")
    sess3 = create_session("user_123")
    
    user_123_sessions = list_user_sessions("user_123")
    assert len(user_123_sessions) == 2 # sess1 (closed) and sess3 (active)
    
    user_456_sessions = list_user_sessions("user_456")
    assert len(user_456_sessions) == 1
    print("Test F Passed\n")

    # 4. Persistence Reload
    print("[TEST E] Persistence & Reload")
    # Verify file exists
    assert os.path.exists(CACHE_FILE)
    
    # Simulate restart by re-initializing a repo
    from apps.backend.session.session_repository import SessionRepository
    new_repo = SessionRepository()
    reloaded_sess = new_repo.get_session(sess3.session_id)
    assert reloaded_sess is not None
    assert reloaded_sess.user_id == "user_123"
    print("Test E Passed\n")

    print("\n=== EXAMPLE SESSION STATE DUMP ===")
    print(json.dumps(sess3.model_dump(), indent=2))

    print("\n=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    run_verification()
