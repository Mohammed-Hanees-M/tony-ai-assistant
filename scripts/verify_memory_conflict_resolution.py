import os
import sys
import json
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.database.session import SessionLocal, engine
from apps.backend.database.base import Base
from apps.backend.database.models import LongTermMemory
from apps.backend.database.repositories.memory_repository import create_long_term_memory
from apps.backend.llm.memory_retriever import retrieve_relevant_long_term_memories
from apps.backend.llm.memory_conflict_resolver import detect_explicit_correction

def verify_conflict_resolution():
    print("=== TONY MEMORY CONFLICT RESOLUTION VERIFICATION (PART 7J) ===")
    
    # Reset DB
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    DUMMY_VEC = [0.1] * 768
    
    with patch("apps.backend.database.repositories.memory_repository.generate_embeddings", return_value=DUMMY_VEC), \
         patch("apps.backend.llm.memory_retriever.generate_embeddings", return_value=DUMMY_VEC):
        
        # 1. Test Explicit Correction Detection
        msg1 = "Actually, my project is called Tony"
        msg2 = "My hobby is coding"
        print(f"\n[Step 1] Testing Correction Detection:")
        print(f"  '{msg1}' is correction: {detect_explicit_correction(msg1)}")
        print(f"  '{msg2}' is correction: {detect_explicit_correction(msg2)}")
        assert detect_explicit_correction(msg1) == True
        assert detect_explicit_correction(msg2) == False
        
        # 2. Setup Initial Fact
        print("\n[Step 2] Storing initial fact...")
        k = "user_name"
        f1 = create_long_term_memory(db, key=k, value="Bob", category="identity", importance=3)
        print(f"  Stored: ID {f1.id} | Key: {f1.key} | Value: {f1.value}")
        
        # 3. Trigger Conflict
        print("\n[Step 3] Storing contradictory fact (Correction)...")
        f2 = create_long_term_memory(db, key=k, value="Alice", category="identity", importance=3)
        print(f"  Stored: ID {f2.id} | Key: {f2.key} | Value: {f2.value}")
        
        # 4. Assert DB State
        db.refresh(f1)
        db.refresh(f2)
        print(f"\n[Step 4] Auditing Supersession Chain:")
        print(f"  Old Fact (ID {f1.id}): Superseded={f1.superseded} | SupersededBy={f1.superseded_by} | Archived={f1.archived}")
        print(f"  New Fact (ID {f2.id}): Supersedes={f2.supersedes} | Active={not f2.superseded}")
        
        assert f1.superseded == True
        assert f1.superseded_by == f2.id
        assert f1.archived == True
        assert f2.supersedes == f1.id
        assert f2.superseded == False
        
        # 5. Verify Retrieval
        print("\n[Step 5] Verifying Retrieval (Belief Gating):")
        # Since they have same embedding, normally both would match. 
        # But filter should exclude ID 1.
        results = retrieve_relevant_long_term_memories(db, "What is my name?")
        print(f"  Retrieval returned {len(results)} results.")
        for r in results:
            print(f"    - ID {r.id}: {r.value}")
            
        found_alice = any(r.value == "Alice" for r in results)
        found_bob = any(r.value == "Bob" for r in results)
        
        print(f"  Alice found: {found_alice}")
        print(f"  Bob found: {found_bob}")
        
        assert found_alice == True
        assert found_bob == False
        
    db.close()
    print("\n=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    verify_conflict_resolution()
