import json
from sqlalchemy.orm import Session
from apps.backend.database.models.memory import LongTermMemory
from apps.backend.llm.inference import generate_embeddings

def create_long_term_memory(db: Session, key: str, value: str, category: str = "fact", importance: int = 1, source_message_id: int | None = None) -> LongTermMemory:
    """
    Creates or updates a long-term memory fact.
    Ensures no duplicate values are stored for the same semantic fact.
    Generates semantic embeddings for each fact.
    """
    # 0. Generate Embedding for the fact value
    vector = generate_embeddings(value)
    embedding_json = json.dumps(vector) if vector else None

    # 1. Deduplicate by EXACT Value (semantic match)
    existing_by_val = db.query(LongTermMemory).filter(LongTermMemory.value == value).first()
    if existing_by_val:
        # If value matches, we update the existing entry (maybe it has a better key now)
        existing_by_val.key = key
        existing_by_val.category = category
        existing_by_val.importance = max(existing_by_val.importance, importance)
        existing_by_val.source_message_id = source_message_id
        existing_by_val.embedding = embedding_json 
        db.commit()
        db.refresh(existing_by_val)
        return existing_by_val

    # 2. Conflict Handling: Deduplicate by Key (e.g. user changes their name)
    # If the key exists but value is different, we SUPERSEDE the old one.
    existing_by_key = db.query(LongTermMemory).filter(
        LongTermMemory.key == key, 
        LongTermMemory.superseded == False
    ).first()
    
    if existing_by_key and existing_by_key.value != value:
        # Create NEW memory as the active truth
        new_memory = LongTermMemory(
            key=key,
            value=value,
            category=category,
            importance=max(existing_by_key.importance, importance),
            source_message_id=source_message_id,
            embedding=embedding_json
        )
        db.add(new_memory)
        db.commit()
        db.refresh(new_memory)
        
        # Link them in a supersession chain
        from apps.backend.llm.memory_conflict_resolver import handle_memory_supersession
        handle_memory_supersession(db, existing_by_key, new_memory)
        
        return new_memory
    
    if existing_by_key:
        # If value is same, just update metadata (idempotent)
        existing_by_key.category = category
        existing_by_key.importance = max(existing_by_key.importance, importance)
        existing_by_key.source_message_id = source_message_id
        db.commit()
        db.refresh(existing_by_key)
        return existing_by_key
    
    # 3. Create New
    memory = LongTermMemory(
        key=key,
        value=value,
        category=category,
        importance=importance,
        source_message_id=source_message_id,
        embedding=embedding_json
    )
    db.add(memory)
    db.commit()
    db.refresh(memory)
    return memory

def get_top_memories(db: Session, limit: int = 10) -> list[LongTermMemory]:
    """Retrieves top N memories sorted by importance and recency."""
    return (
        db.query(LongTermMemory)
        .order_by(LongTermMemory.importance.desc(), LongTermMemory.id.desc())
        .limit(limit)
        .all()
    )

def get_all_memories(db: Session) -> list[LongTermMemory]:
    """Retrieves all memories with embeddings for vector search."""
    return db.query(LongTermMemory).all()
