import re

def is_sensitive(text: str) -> bool:
    """Checks if the text likely contains sensitive information or credentials."""
    sensitive_keywords = [
        "api key", "password", "token", "secret key", "credential", 
        "private key", "access key", "auth key", "bearer"
    ]
    text_lower = text.lower()
    return any(kw in text_lower for kw in sensitive_keywords)

def extract_long_term_memories(content: str) -> list[dict]:
    """
    Heuristic-based extraction of long-term facts from user messages.
    Returns a list of dicts with keys: key, value, importance.
    Includes a safety filter to block sensitive data.
    """
    memories = []
    # Split by common delimiters but avoid splitting URLs (period must be followed by space)
    segments = re.split(r'\.\s+|\band\b|,', content.lower())
    
    for segment in segments:
        segment = segment.strip()
        if not segment:
            continue

        extracted_item = None

        # 1. Identity / Name
        name_match = re.search(r"^my name is ([\w\s]+)[.!?]?$", segment)
        if name_match:
            extracted_item = {
                "key": "user_name",
                "value": name_match.group(1).strip().title(),
                "category": "identity",
                "importance": 5
            }

        # 2. General Identity (I am a...)
        elif identity_match := re.search(r"^i am (?:a|an) ([\w\s]+)[.!?]?$", segment):
            avoid = ["fine", "good", "happy", "sad", "tired", "hungry", "ok", "okay"]
            val = identity_match.group(1).strip()
            if val not in avoid and len(val) > 2:
                extracted_item = {
                    "key": "user_identity",
                    "value": val,
                    "category": "identity",
                    "importance": 4
                }

        # 3. Preferences / Favorites
        elif fav_match := re.search(r"^my favorite ([\w\s]+) is ([\w\s]+)[.!?]?$", segment):
            fav_key = f"fav_{fav_match.group(1).strip().replace(' ', '_')}"
            extracted_item = {
                "key": fav_key,
                "value": fav_match.group(2).strip(),
                "category": "preference",
                "importance": 3
            }
        
        # 4. Likes
        elif like_match := re.search(r"^i (?:really )?like ([\w\s]{3,})[.!?]?$", segment):
            val = like_match.group(1).strip()
            extracted_item = {
                "key": f"preference_{val.replace(' ', '_')}",
                "value": f"User likes {val}",
                "category": "preference",
                "importance": 3
            }

        # 5. Explicit Memory Directives
        elif rem_match := re.search(r"(?:remember that|don't forget|save this|keep in mind)[\s:]+([\w\s,.'\"\-:/]+)", segment):
            fact_val = rem_match.group(1).strip()
            emotional_states = ["happy", "sad", "angry", "tired", "bored", "good", "fine"]
            # Determine sub-category
            cat = "fact"
            if any(k in fact_val.lower() for k in ["meeting", "tomorrow", "schedule", "at ", "pm", "am"]):
                cat = "schedule"
            elif any(k in fact_val.lower() for k in ["work", "project", "building"]):
                cat = "work"

            if not any(state in fact_val for state in emotional_states) and len(fact_val) > 10:
                import zlib
                fact_id = zlib.adler32(fact_val.encode()) & 0xffffffff
                extracted_item = {
                    "key": f"fact_{fact_id}", 
                    "value": fact_val,
                    "category": cat,
                    "importance": 5
                }

        # 6. Project / Context
        elif project_match := re.search(r"(?:we are building|i am working on|this project is) ([\w\s,.'\"-]+)", segment):
            val = project_match.group(1).strip()
            if len(val) > 3:
                extracted_item = {
                    "key": "project_context",
                    "value": val,
                    "category": "project",
                    "importance": 5
                }

        # SAFETY FILTER: Apply sensitive data protection
        if extracted_item:
            if is_sensitive(extracted_item["value"]) or is_sensitive(extracted_item["key"]):
                print(f"[SECURITY] Blocked extraction of potentially sensitive data: '{extracted_item['key']}'")
            else:
                memories.append(extracted_item)

    return memories
