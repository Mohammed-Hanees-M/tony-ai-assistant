from typing import List, Dict
from apps.backend.llm.memory_priority import score_message_importance

def estimate_tokens(content: str) -> int:
    """
    Estimates the number of tokens in a string.
    Currently uses a simple heuristic: characters / 4.
    """
    if not content:
        return 0
    return max(1, len(content) // 4)

def count_message_tokens(message: Dict[str, str]) -> int:
    """Estimates tokens for a single message."""
    return estimate_tokens(message.get("content", ""))

def calculate_total_tokens(msgs: List[Dict[str, str]]) -> int:
    return sum(count_message_tokens(m) for m in msgs)

def trim_messages_to_token_budget(messages: List[Dict[str, str]], max_tokens: int) -> List[Dict[str, str]]:
    """
    Trims a list of messages based on importance scoring.
    Always preserves the system message (first) and the current user message (last).
    Lowest importance turns are removed first. Ties are broken by oldest-first.
    """
    if not messages or len(messages) <= 2:
        return messages

    total_tokens = calculate_total_tokens(messages)
    
    if total_tokens <= max_tokens:
        print(f"[DEBUG] Token budget pass: {total_tokens} <= {max_tokens}. No trimming needed.")
        return messages

    print(f"[DEBUG] Token budget overflow: {total_tokens} > {max_tokens}. Prioritizing trimming...")
    
    # Identify fixed parts
    system_msg = messages[0]
    current_user_msg = messages[-1]
    history = messages[1:-1]
    
    # 1. Group into turns (User + Assistant pairs)
    turns = []
    i = 0
    while i < len(history):
        # We assume standard U, A, U, A...
        # If we see U, A -> that's a turn.
        # If we see something else (e.g. orphaned message), we treat it as its own turn.
        turn_msgs = [history[i]]
        if i + 1 < len(history) and history[i]["role"] == "user" and history[i+1]["role"] == "assistant":
            turn_msgs.append(history[i+1])
            i += 2
        else:
            # Orphaned message
            i += 1
        
        # Calculate importance score for the turn
        # We take the MAX of messages in the turn to ensure important facts preserve the context.
        importance = max(score_message_importance(m) for m in turn_msgs)
        
        turns.append({
            "messages": turn_msgs,
            "importance": importance,
            "original_index": len(turns) # For tie-breaking (oldest-first)
        })

    # 2. Repeatedly remove lowest-priority turn until under budget
    while calculate_total_tokens([system_msg] + [m for t in turns for m in t["messages"]] + [current_user_msg]) > max_tokens and turns:
        # Find the turn with the lowest (importance, index)
        # Sorting priority: 1. Importance (Ascending), 2. Original Index (Ascending - Oldest)
        turns.sort(key=lambda t: (t["importance"], t["original_index"]))
        
        removed_turn = turns.pop(0)
        u_preview = removed_turn["messages"][0]["content"][:20]
        score = removed_turn["importance"]
        print(f"[DEBUG] Trimming turn (Score: {score}): '{u_preview}...' chosen because it has lowest priority.")
        
    # 3. Rebuild message list in original chronological order
    turns.sort(key=lambda t: t["original_index"])
    
    final_messages = [system_msg]
    for turn in turns:
        final_messages.extend(turn["messages"])
    final_messages.append(current_user_msg)
    
    final_tokens = calculate_total_tokens(final_messages)
    print(f"[DEBUG] Trimming result: Tokens {total_tokens} -> {final_tokens}")
    
    return final_messages
