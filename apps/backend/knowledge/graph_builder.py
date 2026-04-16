import json
import re
from typing import List, Tuple, Dict
from apps.backend.schemas.knowledge import KnowledgeEntity, KnowledgeRelation
from apps.backend.llm.inference import run_llm_inference

TRIPLE_EXTRACTION_PROMPT = """You are Tony's Graph Knowledge Extractor. Extract entity-relation-entity triples from the text.
Use canonical forms if possible. 

Output strictly a JSON list of objects:
[
  {
    "subject": "TonyLabs",
    "subject_type": "organization",
    "relation": "builds",
    "object": "AI software",
    "object_type": "product"
  }
]
"""

class InMemoryGraphStore:
    def __init__(self):
        self.entities: Dict[str, KnowledgeEntity] = {}
        self.relations: List[KnowledgeRelation] = []

    def get_or_create_entity(self, name: str, etype: str) -> KnowledgeEntity:
        canonical = name.lower().strip()
        for ent in self.entities.values():
            if ent.canonical_name.lower().strip() == canonical:
                return ent
        
        ent = KnowledgeEntity(canonical_name=name, entity_type=etype)
        self.entities[ent.entity_id] = ent
        return ent

    def add_relation(self, source_id: str, rel_type: str, target_id: str, confidence: float = 1.0) -> KnowledgeRelation:
        # deduplicate relations
        for r in self.relations:
            if r.source_entity_id == source_id and r.target_entity_id == target_id and r.relation_type == rel_type:
                return r
                
        rel = KnowledgeRelation(source_entity_id=source_id, relation_type=rel_type, target_entity_id=target_id, confidence=confidence)
        self.relations.append(rel)
        return rel

def extract_knowledge_triples(text: str, model: str = "phi3") -> List[dict]:
    messages = [
        {"role": "system", "content": TRIPLE_EXTRACTION_PROMPT},
        {"role": "user", "content": f"Text: {text}"}
    ]
    raw = run_llm_inference(messages, model)
    try:
        match = re.search(r'\[\s*\{.*?\}\s*\]', raw, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return []
    except Exception as e:
        print(f"[GRAPH EXTRACTOR] Malformed output safely caught: {e}")
        return []

def ingest_memory_into_graph(text: str, store: InMemoryGraphStore, model: str = "phi3") -> List[KnowledgeRelation]:
    triples = extract_knowledge_triples(text, model)
    new_relations = []
    
    for t in triples:
        subj = t.get("subject")
        subj_type = t.get("subject_type", "unknown")
        rel = t.get("relation")
        obj = t.get("object")
        obj_type = t.get("object_type", "unknown")
        
        if subj and rel and obj:
            s_ent = store.get_or_create_entity(subj, subj_type)
            o_ent = store.get_or_create_entity(obj, obj_type)
            new_rel = store.add_relation(s_ent.entity_id, rel, o_ent.entity_id)
            new_relations.append(new_rel)
            print(f"[GRAPH BUILDER] Stored Base Triple: ({s_ent.canonical_name}) -[{rel}]-> ({o_ent.canonical_name})")
            
    return new_relations
