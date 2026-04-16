import json
import os
import time
from typing import Dict, Optional, List
from apps.backend.schemas.session import ConversationSession

CACHE_FILE = "session_store.json"

class SessionRepository:
    def __init__(self):
        self._sessions: Dict[str, ConversationSession] = self._load()

    def _load(self) -> Dict[str, ConversationSession]:
        if not os.path.exists(CACHE_FILE):
            return {}
        try:
            with open(CACHE_FILE, "r") as f:
                data = json.load(f)
                return {sid: ConversationSession(**s) for sid, s in data.items()}
        except:
            return {}

    def _save(self):
        try:
            with open(CACHE_FILE, "w") as f:
                json.dump({sid: s.model_dump() for sid, s in self._sessions.items()}, f, indent=2)
        except Exception as e:
            print(f"[SESSION REPO] Save error: {e}")

    def save_session(self, session: ConversationSession):
        self._sessions[session.session_id] = session
        self._save()

    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        return self._sessions.get(session_id)

    def list_user_sessions(self, user_id: str) -> List[ConversationSession]:
        return [s for s in self._sessions.values() if s.user_id == user_id]

    def delete_session(self, session_id: str):
        if session_id in self._sessions:
            del self._sessions[session_id]
            self._save()

GLOBAL_SESSION_REPO = SessionRepository()
