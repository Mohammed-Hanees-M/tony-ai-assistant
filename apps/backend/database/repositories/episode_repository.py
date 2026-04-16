from sqlalchemy.orm import Session
from apps.backend.database.models.episode import EpisodicMemory

def create_episodic_memory(
    db: Session, 
    conversation_id: int, 
    event_type: str, 
    summary: str, 
    outcome: str, 
    importance: int, 
    tags: str, 
    embedding: str = None
):
    episode = EpisodicMemory(
        conversation_id=conversation_id,
        event_type=event_type,
        summary=summary,
        outcome=outcome,
        importance=importance,
        tags=tags,
        embedding=embedding
    )
    db.add(episode)
    db.commit()
    db.refresh(episode)
    return episode
