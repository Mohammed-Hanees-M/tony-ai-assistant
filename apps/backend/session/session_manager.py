import time
import uuid
from typing import Optional, List
from apps.backend.schemas.session import ConversationSession
from apps.backend.session.session_repository import GLOBAL_SESSION_REPO
from apps.backend.streaming.streaming_engine import cancel_stream

def create_session(user_id: str, metadata: dict = None) -> ConversationSession:
    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    session = ConversationSession(
        session_id=session_id,
        user_id=user_id,
        metadata=metadata or {}
    )
    GLOBAL_SESSION_REPO.save_session(session)
    print(f"[SESSION] Created session {session_id} for user {user_id}")
    return session

def get_session(session_id: str) -> Optional[ConversationSession]:
    session = GLOBAL_SESSION_REPO.get_session(session_id)
    if session:
        session.last_active_at = time.time()
        GLOBAL_SESSION_REPO.save_session(session)
    return session

def close_session(session_id: str):
    session = GLOBAL_SESSION_REPO.get_session(session_id)
    if not session:
        return
        
    # Cancel any active stream
    if session.active_stream_id:
        print(f"[SESSION] Closing session {session_id}. Cancelling active stream {session.active_stream_id}")
        cancel_stream(session.active_stream_id)
        
    session.status = "closed"
    session.active_stream_id = None
    GLOBAL_SESSION_REPO.save_session(session)
    print(f"[SESSION] Closed session {session_id}")

def link_stream_to_session(session_id: str, stream_id: str):
    session = GLOBAL_SESSION_REPO.get_session(session_id)
    if session:
        # If there's already an active stream, we might want to cancel it (exclusive mode)
        if session.active_stream_id and session.active_stream_id != stream_id:
            cancel_stream(session.active_stream_id)
            
        session.active_stream_id = stream_id
        session.last_active_at = time.time()
        GLOBAL_SESSION_REPO.save_session(session)
        print(f"[SESSION] Linked stream {stream_id} to session {session_id}")

def list_user_sessions(user_id: str) -> List[ConversationSession]:
    return GLOBAL_SESSION_REPO.list_user_sessions(user_id)
