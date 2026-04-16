import os
import sys
import json
from datetime import datetime

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.database.models.memory import LongTermMemory
from apps.backend.llm.memory_provenance import assign_provenance, get_memory_provenance, format_memory_explanation

def run_verification():
    print("=== TONY MEMORY PROVENANCE VERIFICATION (PART 7L) ===\n")

    timestamp = datetime(2026, 4, 13, 12, 0, 0)
    
    # A & C & D: Explicit fact with excerpt and linkage
    mem_explicit = LongTermMemory(key="favorite_color", value="Blue")
    assign_provenance(
        mem_explicit, 
        source_type="user_explicit", 
        message_id=101, 
        conversation_id=5, 
        excerpt="my favorite color is Blue",
        timestamp=timestamp
    )
    
    prov_ex = get_memory_provenance(mem_explicit)
    print("Test A: Explicit provenance saved.")
    assert prov_ex['source_type'] == 'user_explicit'
    
    print(f"Test C: Source excerpt preserved: '{prov_ex['source_excerpt']}'")
    assert prov_ex['source_excerpt'] == "my favorite color is Blue"
    
    print(f"Test D: Message linkage works: msg_id={prov_ex['source_message_id']}, conv_id={prov_ex['source_conversation_id']}")
    assert prov_ex['source_message_id'] == 101
    assert prov_ex['source_conversation_id'] == 5
    
    expl_ex = format_memory_explanation(mem_explicit)
    print(f"Test E (Explicit): {expl_ex}")
    assert "you told me" in expl_ex

    # B: Inferred memory
    mem_inferred = LongTermMemory(key="stress_level", value="High")
    assign_provenance(
        mem_inferred,
        source_type="inferred_extraction",
        message_id=102,
        conversation_id=5,
        excerpt="I've been working 80 hours this week",
        timestamp=timestamp
    )
    prov_inf = get_memory_provenance(mem_inferred)
    print("\nTest B: Inferred provenance saved.")
    assert prov_inf['source_type'] == 'inferred_extraction'
    
    expl_inf = format_memory_explanation(mem_inferred)
    print(f"Test E (Inferred): {expl_inf}")
    assert "inferred" in expl_inf
    assert "80 hours this week" in expl_inf
    
    # F: Evidence chain
    mem_derived = LongTermMemory(key="likes_dogs", value="Yes")
    evidence = [
        {"type": "message", "id": 50, "excerpt": "I love golden retrievers"},
        {"type": "episode", "id": 12, "excerpt": "User adopted a puppy"}
    ]
    assign_provenance(
        mem_derived,
        source_type="summary",
        evidence_chain=evidence
    )
    
    prov_der = get_memory_provenance(mem_derived)
    print(f"\nTest F: Evidence chain preserved with {len(prov_der['evidence_chain'])} items")
    assert len(prov_der['evidence_chain']) == 2
    assert prov_der['evidence_chain'][0]['type'] == 'message'
    
    expl_der = format_memory_explanation(mem_derived)
    print(f"Test E (Summary Derived): {expl_der}")

    print("\n=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    run_verification()
