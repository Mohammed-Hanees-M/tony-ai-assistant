import json

def assign_provenance(memory, source_type: str, message_id: int = None, conversation_id: int = None, excerpt: str = None, timestamp=None, evidence_chain: list = None):
    """
    Populates provenance metadata during memory creation.
    """
    memory.source_type = source_type
    
    if message_id is not None:
        memory.source_message_id = message_id
    if conversation_id is not None:
        memory.source_conversation_id = conversation_id
    if excerpt is not None:
        memory.source_excerpt = excerpt
    if timestamp is not None:
        memory.source_timestamp = timestamp
    if evidence_chain is not None:
        memory.evidence_chain = json.dumps(evidence_chain)
        
    return memory

def get_memory_provenance(memory):
    """
    Returns a dictionary of the memory's provenance metadata.
    """
    evidence = []
    if getattr(memory, 'evidence_chain', None):
        try:
            evidence = json.loads(memory.evidence_chain)
        except:
            pass
            
    return {
        "source_type": getattr(memory, 'source_type', 'unknown'),
        "source_message_id": getattr(memory, 'source_message_id', None),
        "source_conversation_id": getattr(memory, 'source_conversation_id', None),
        "source_excerpt": getattr(memory, 'source_excerpt', None),
        "source_timestamp": getattr(memory, 'source_timestamp', None),
        "evidence_chain": evidence
    }

def format_memory_explanation(memory):
    """
    Formats a natural language explanation of where a memory came from.
    """
    prov = get_memory_provenance(memory)
    source_type = prov['source_type']
    
    ts_str = ""
    if prov['source_timestamp']:
        ts = prov['source_timestamp']
        if hasattr(ts, 'strftime'):
            ts_str = f" on {ts.strftime('%Y-%m-%d %H:%M:%S')}"
        else:
            ts_str = f" on {ts}"

    if source_type == 'user_explicit':
        explanation = f"I know this because you told me{ts_str}"
        if prov['source_excerpt']:
             explanation += f" ('{prov['source_excerpt']}')."
        else:
             explanation += "."
    elif source_type == 'inferred_extraction':
        if prov['source_excerpt']:
            explanation = f"This was inferred from prior interactions{ts_str}, specifically when you mentioned '{prov['source_excerpt']}'."
        else:
            explanation = f"This was inferred from prior interactions{ts_str}."
    elif source_type == 'summary':
        explanation = "This was derived from a summary of a past conversation."
    elif source_type == 'reflection':
        explanation = "This is a learned lesson from reflecting on our discussions."
    elif source_type == 'episode':
        explanation = "This is based on a recorded past experience."
    else:
        explanation = "This is from my general stored knowledge."

    return explanation
