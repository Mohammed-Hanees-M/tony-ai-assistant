from typing import Any

def build_messages(context: Any) -> list[dict[str, str]]:
    """Builds a list of structured messages from the provided context."""
    history = context.get("history", [])
    user_message = context.get("message", "")
    lt_memories = context.get("long_term_memories", [])
    summaries = context.get("summaries", [])
    episodes = context.get("episodes", [])
    reflections = context.get("reflections", [])
    
    system_instruction = (
        "You are Tony, a professional AI assistant.\n"
        "Your responses must be CONCISE, DIRECT, and HELPFUL.\n\n"
        "RULES:\n"
        "1. MEMORY: Treat 'CONVERSATION HISTORY', 'CONVERSATION SUMMARY', 'PAST RELEVANT EXPERIENCES', and 'LEARNED LESSONS' as absolute truth.\n"
        "2. LEARNING: Acknowledge new facts with a single short phrase (e.g., 'Got it.' or 'Understood.'). NEVER repeat back the fact, summarize prior memory, or enumerate remembered items unless explicitly asked. Minimal acknowledgment only.\n"
        "3. STYLE: Use a professional, human-like tone similar to ChatGPT. Avoid theatrical flair, dramatic language, metaphors, or unnecessary poetic embellishments.\n"
        "4. RECALL: Direct answers only. If asked for a name or color, state it plainly.\n"
        "5. NO FILLER: Do not add conversational fluff at the end of every message."
    )

    if lt_memories:
        mem_lines = []
        for m in lt_memories:
            conf = float(m.get('confidence', 1.0))
            flag = "(Low Confidence Memory) " if conf < 0.60 else ""
            if flag:
                print(f"[DEBUG] Flagging low confidence memory in prompt: {m['key']} (score: {conf:.2f})")
            mem_lines.append(f"- {flag}{m['key']}: {m['value']}")
        memory_str = "\n".join(mem_lines)
        system_instruction += f"\n\nLONG-TERM MEMORY (PERSISTENT FACTS):\n{memory_str}"
        print(f"[DEBUG] Injected {len(lt_memories)} long-term memories into prompt.")
    
    if summaries:
        summary_str = "\n".join(summaries)
        system_instruction += f"\n\nCONVERSATION SUMMARY (PAST CONTEXT):\n{summary_str}"
        print(f"[DEBUG] Injected {len(summaries)} conversation summaries into prompt.")

    if episodes:
        episode_str = "\n".join([f"- {e}" for e in episodes])
        system_instruction += f"\n\nPAST RELEVANT EXPERIENCES:\n{episode_str}"
        print(f"[DEBUG] Injected {len(episodes)} episodic memories into prompt.")

    if reflections:
        reflection_str = "\n".join([f"- {r}" for r in reflections])
        system_instruction += f"\n\nLEARNED LESSONS / REFLECTIONS:\n{reflection_str}"
        print(f"[DEBUG] Injected {len(reflections)} reflective memories into prompt.")
    
    messages = [
        {"role": "system", "content": system_instruction}
    ]
    
    # Add history
    for msg in history:
        messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })
        
    # Add current message
    messages.append({
        "role": "user",
        "content": user_message
    })
    
    return messages
