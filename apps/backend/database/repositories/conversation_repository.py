from sqlalchemy.orm import Session
from apps.backend.database.models.conversation import Conversation
from apps.backend.database.models.message import Message

def create_conversation(db: Session) -> Conversation:
    conversation = Conversation()
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation

def get_conversation(db: Session, conversation_id: int):
    return db.query(Conversation).filter(Conversation.id == conversation_id).first()

def add_message(db: Session, conversation_id: int, role: str, content: str) -> Message:
    message = Message(conversation_id=conversation_id, role=role, content=content)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message

def get_messages(db: Session, conversation_id: int):
    return db.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.id.asc()).all()

def get_recent_messages(db: Session, conversation_id: int, limit: int = 10):
    """
    Retrieves the most recent N messages for a conversation,
    returned in chronological order.
    """
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.id.desc())
        .limit(limit)
        .all()
    )
    # Reverse to restore chronological order (oldest -> newest)
    return messages[::-1]

def get_messages_after_id(db: Session, conversation_id: int, after_id: int):
    """Retrieves all messages in a conversation following a specific ID."""
    return (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id, Message.id > after_id)
        .order_by(Message.id.asc())
        .all()
    )
