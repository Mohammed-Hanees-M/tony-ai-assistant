from typing import List, Tuple
from apps.backend.schemas.knowledge import KnowledgeEntity, KnowledgeRelation
from apps.backend.knowledge.graph_builder import InMemoryGraphStore

def traverse_related_entities(store: InMemoryGraphStore, entity_name: str, max_hops: int = 1) -> List[Tuple[str, str, str]]:
    paths = []
    canonical = entity_name.lower().strip()
    
    start_ent = None
    for e in store.entities.values():
        if e.canonical_name.lower().strip() == canonical:
            start_ent = e
            break
            
    if not start_ent:
        return paths

    def _traverse(cur_id: str, depth: int):
        if depth >= max_hops:
            return
        
        for r in store.relations:
            if not r.active: continue
            if r.source_entity_id == cur_id:
                t_ent = store.entities.get(r.target_entity_id)
                s_ent = store.entities.get(cur_id)
                if t_ent and s_ent:
                    triple = (s_ent.canonical_name, r.relation_type, t_ent.canonical_name)
                    if triple not in paths:
                        paths.append(triple)
                        _traverse(r.target_entity_id, depth + 1)
                        
    _traverse(start_ent.entity_id, 0)
    print(f"[GRAPH ENGINE] Traversed {len(paths)} unique knowledge connections starting from '{entity_name}'.")
    return paths

def query_relation_path(store: InMemoryGraphStore, source: str, relation_chain: List[str]) -> List[str]:
    # Placeholder for future graph embedding integrations & neural path matching
    return []

def fuse_with_memory_retrieval(graph_triples: List[Tuple], semantic_results: List[str]) -> str:
    print("[RETRIEVAL ENGINE] Enacting Multi-Modal Retrieval Fusion (Graph + Semantic)...")
    
    context = "=== GRAPH KNOWLEDGE MATRIX ===\n"
    for s, r, o in graph_triples:
        context += f"- {s} {r} {o}\n"
        
    context += "\n=== SEMANTIC EPISODIC MEMORY ===\n"
    context += "\n".join(semantic_results)
    
    return context
