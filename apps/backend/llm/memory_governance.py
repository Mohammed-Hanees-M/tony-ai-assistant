import math
import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from apps.backend.database.models import LongTermMemory, EpisodicMemory, ReflectiveMemory

# GOVERNANCE CONFIG
DECAY_HALF_LIFE_DAYS = 30.0
ARCHIVE_THRESHOLD = 0.15

def compute_memory_strength(memory):
    """
    Computes the current strength score of a memory based on importance, 
    recency, access frequency, and reinforcement.
    """
    now = datetime.now(timezone.utc)
    
    # Ensure created_at is naive-comparison safe
    created_at = memory.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
        
    age_days = (now - created_at).total_seconds() / (24 * 3600)
    
    # 1. Base Importance (0.2 to 1.0)
    importance_factor = max(0.2, memory.importance / 5.0)
    
    # 2. Time Decay (Exponential)
    decay_factor = math.pow(2, -age_days / DECAY_HALF_LIFE_DAYS)
    
    # 3. Access Bonus (Logarithmic diminishing returns)
    access_factor = math.log1p(memory.access_count) * 0.2
    
    # 4. Reinforcement Bonus
    reinforcement_factor = memory.reinforcement_count * 0.1
    
    # 5. Recency Bonus
    recency_factor = 0
    if memory.last_accessed_at:
        last_acc = memory.last_accessed_at
        if last_acc.tzinfo is None:
            last_acc = last_acc.replace(tzinfo=timezone.utc)
        last_acc_days = (now - last_acc).total_seconds() / (24 * 3600)
        recency_factor = math.pow(2, -last_acc_days / 7.0) * 0.3 
        
    strength = (importance_factor * decay_factor) + access_factor + reinforcement_factor + recency_factor
    
    return round(min(1.0, strength), 4)

def reinforce_memory(db: Session, memory):
    """Updates usage metadata for a memory when it is retrieved."""
    memory.access_count += 1
    memory.last_accessed_at = datetime.now(timezone.utc)
    memory.strength_score = compute_memory_strength(memory)
    db.commit()

def mark_reinforcement_positive(db: Session, memory):
    """Specifically rewards a memory that was positively affirmed in conversation."""
    memory.reinforcement_count += 1
    memory.strength_score = compute_memory_strength(memory)
    db.commit()

def run_memory_governance_cycle(db: Session):
    """
    Scans all memory tiers, recomputes strength, and archives weak/stale memories.
    """
    print("=== STARTING MEMORY GOVERNANCE CYCLE ===")
    
    models = [LongTermMemory, EpisodicMemory, ReflectiveMemory]
    total_archived = 0
    total_processed = 0
    
    for model in models:
        # Process only active memories
        memories = db.query(model).filter(model.archived == False).all()
        for m in memories:
            total_processed += 1
            old_strength = m.strength_score
            new_strength = compute_memory_strength(m)
            m.strength_score = new_strength
            
            # Archive Decision
            if new_strength < ARCHIVE_THRESHOLD and not m.decay_exempt:
                m.archived = True
                total_archived += 1
                type_name = model.__name__
                print(f"[ARCHIVE] {type_name} ID {m.id} | Strength {new_strength:.4f} < {ARCHIVE_THRESHOLD} | Reason: Stale/Weak")
            
    db.commit()
    print(f"=== GOVERNANCE CYCLE COMPLETE: Processed {total_processed}, Archived {total_archived} ===")
    return total_processed, total_archived
