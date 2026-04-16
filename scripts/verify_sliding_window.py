import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.database.base import Base
from apps.backend.database.models.conversation import Conversation
from apps.backend.database.models.message import Message
from apps.backend.database.repositories.conversation_repository import add_message, get_recent_messages, create_conversation
from apps.backend.core.config import CONTEXT_WINDOW_SIZE

# Setup In-Memory SQLite for testing
engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def verify_sliding_window():
    print(f"Starting verification for CONTEXT_WINDOW_SIZE = {CONTEXT_WINDOW_SIZE}...")
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    try:
        # 1. Create a conversation
        conv = create_conversation(db)
        conv_id = conv.id
        print(f"Created conversation ID: {conv_id}")
        
        # 2. Insert 15 messages
        total_messages = 15
        for i in range(total_messages):
            role = "user" if i % 2 == 0 else "assistant"
            content = f"Message {i+1}"
            add_message(db, conv_id, role, content)
        
        print(f"Inserted {total_messages} messages.")
        
        # 3. Retrieve recent messages with the sliding window size
        recent_messages = get_recent_messages(db, conv_id, limit=CONTEXT_WINDOW_SIZE)
        
        # Verification A: Count check
        print(f"Retrieved {len(recent_messages)} messages.")
        assert len(recent_messages) == CONTEXT_WINDOW_SIZE, f"Expected {CONTEXT_WINDOW_SIZE} messages, got {len(recent_messages)}"
        
        # Verification B: Content check (should be messages 6 to 15)
        # Message 1 indexed 0, so messages 6-15 have content "Message 6" to "Message 15"
        expected_first_content = f"Message {total_messages - CONTEXT_WINDOW_SIZE + 1}"
        expected_last_content = f"Message {total_messages}"
        
        assert recent_messages[0].content == expected_first_content, f"First message should be '{expected_first_content}', got '{recent_messages[0].content}'"
        assert recent_messages[-1].content == expected_last_content, f"Last message should be '{expected_last_content}', got '{recent_messages[-1].content}'"
        
        # Verification C: Chronological Order check
        for i in range(len(recent_messages) - 1):
            assert recent_messages[i].id < recent_messages[i+1].id, f"Order is not chronological at index {i}"
        
        print("VERIFICATION SUCCESSFUL: Sliding Window behavior confirmed.")
        print(f"   Window contains messages: {[m.content for m in recent_messages]}")
        
    except Exception as e:
        print(f"VERIFICATION FAILED: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    verify_sliding_window()
