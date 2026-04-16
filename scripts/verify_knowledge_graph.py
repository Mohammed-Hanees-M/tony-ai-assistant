import os
import sys
import json
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.knowledge.graph_builder import InMemoryGraphStore, ingest_memory_into_graph, extract_knowledge_triples
from apps.backend.knowledge.graph_retriever import traverse_related_entities, fuse_with_memory_retrieval

def mock_inference(messages, model):
    content = messages[1]["content"] if len(messages) > 1 else ""
    
    if "Malformed" in content:
        return "Not JSON data"
        
    return json.dumps([
        {
            "subject": "Tony",
            "subject_type": "person",
            "relation": "works_for",
            "object": "TonyLabs",
            "object_type": "organization"
        },
        {
            "subject": "TonyLabs", # Tests deduplication implicitly due to same name
            "subject_type": "organization",
            "relation": "built",
            "object": "AI Assistant",
            "object_type": "product"
        }
    ])

def run_verification():
    print("=== TONY KNOWLEDGE GRAPH SIMULATION VERIFICATION (PART 8R) ===\n")
    
    with patch("apps.backend.knowledge.graph_builder.run_llm_inference", side_effect=mock_inference):

        store = InMemoryGraphStore()
        
        # Test A, F: Triples Extracted & Fallbacks Secure
        print("[TEST A, F] Extraction & JSON Mapping Rules")
        res_ext = extract_knowledge_triples("Tony works at TonyLabs")
        assert len(res_ext) == 2
        bad_ext = extract_knowledge_triples("Malformed Data")
        assert len(bad_ext) == 0
        print("Tests A, F Passed\n")
        
        # Test B, C: Entities normalized/deducted and Relations stored
        print("[TEST B, C] Ingestion and Semantic Deduplication")
        rels = ingest_memory_into_graph("Tony works at TonyLabs. TonyLabs built AI Assistant.", store)
        assert len(store.entities) == 3, "Failed entity deduplication (Tony, TonyLabs, AI Assistant)"
        assert len(store.relations) == 2, "Failed to map base relations correctly!"
        print("Tests B, C Passed\n")
        
        # Test D: Traversal Multi-Hop Engine works accurately 
        print("[TEST D] Graph Traversal Pathfinding")
        paths_single = traverse_related_entities(store, "tony", max_hops=1)
        assert len(paths_single) == 1, "Should only hit 1 hop: Tony -> works_for -> TonyLabs"
        
        paths_multi = traverse_related_entities(store, "tony", max_hops=2)
        assert len(paths_multi) == 2, "Failed multi-hop. Should hit both Tony->TonyLabs and TonyLabs->AI Assistant"
        print("Test D Passed\n")
        
        # Test E: Memory Core Retrieval Fusion Works
        print("[TEST E] Semantic + Graph Modality Fusion")
        fused = fuse_with_memory_retrieval(paths_multi, ["User requested tracking.", "Tony built it."])
        assert "=== GRAPH KNOWLEDGE MATRIX ===" in fused
        assert "Tony works_for TonyLabs" in fused
        assert "TonyLabs built AI Assistant" in fused
        assert "=== SEMANTIC EPISODIC MEMORY ===" in fused
        print("Test E Passed\n")
        
        print("\n=== RAW GRAPH TRACE DUMP ===")
        print(fused)

    print("\n=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    run_verification()
