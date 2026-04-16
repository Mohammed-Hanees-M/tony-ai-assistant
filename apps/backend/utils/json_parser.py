import json
import re
from typing import Any, Dict, Optional, Union

def safe_parse_json(text: str, fallback: Any = None) -> Any:
    """
    Hyper-resilient JSON parser for LLM outputs.
    Extracts, cleans, and repairs JSON-like structures.
    """
    if not text or not isinstance(text, str):
        return fallback

    # 1. Direct parse attempt
    clean_text = text.strip()
    try:
        return json.loads(clean_text)
    except json.JSONDecodeError:
        pass

    # 2. Extract potential start
    match = re.search(r'(\{|\[)', clean_text)
    if not match:
        return fallback
    
    start_index = match.start()
    potential_json = clean_text[start_index:]
    
    # 3. Try to find the matching end or just take the rest and repair
    # Pre-process single quotes to double quotes for common LLM errors
    potential_json = potential_json.replace("'", '"')

    # Try different truncate points if there's trailing garbage
    for i in range(len(potential_json), 0, -1):
        candidate = potential_json[:i]
        
        # Incremental repair: Add missing closing symbols
        for repair_pass in range(3):
             target = candidate
             if repair_pass == 1: target += "}"
             if repair_pass == 2: target += '"]}'
             
             # Brute balance
             while target.count('{') > target.count('}'): target += '}'
             while target.count('[') > target.count(']'): target += ']'
             
             try:
                 return json.loads(target)
             except:
                 continue

    print(f"[JSON PARSER WARNING] Failed to recover JSON from: {text[:50]}...")
    return fallback
