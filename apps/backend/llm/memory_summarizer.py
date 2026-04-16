from typing import List, Dict
from apps.backend.llm.inference import run_llm_inference
from apps.backend.llm.router import route_model

def summarize_conversation_chunk(messages: List[Dict[str, str]]) -> str:
    """
    Generates a concise, structured summary of a list of messages.
    """
    if not messages:
        return ""

    formatted_history = ""
    for msg in messages:
        role = "Hanees" if msg["role"] == "user" else "Tony"
        formatted_history += f"{role}: {msg['content']}\n"

    prompt = [
        {
            "role": "system",
            "content": (
                "You are Tony's memory consolidation engine. Your goal is to preserve CONCRETE FACTUAL CONTEXT while being strictly bounded by the provided text.\n"
                "RULES:\n"
                "1. Format ONLY as a short bulleted list of facts and decisions.\n"
                "2. NO meta-narrative (DO NOT say: 'They discussed', 'The conversation focused on').\n"
                "3. STRICT GROUNDING: Summarize ONLY what is in the 'CONVERSATION CHUNK'. Do NOT use external knowledge, prior memories, or project names (e.g. CLIICXNET) unless explicitly mentioned in the chunk.\n"
                "4. One line per point. Be direct.\n"
                "5. If no specific facts/decisions are found, return 'Routine conversation logs.'\n"
                "\nEXAMPLE OUTPUT:\n"
                "- Fact: User's favorite color is blue.\n"
                "- Decision: Implement the frontend using React."
            )
        },
        {
            "role": "user",
            "content": f"CONVERSATION CHUNK:\n{formatted_history}\n\nSUMMARY:"
        }
    ]

    print(f"[DEBUG] Summarizing {len(messages)} messages...")
    model = route_model("", purpose="summarization")
    summary = run_llm_inference(prompt, model)
    
    if summary.startswith("[Error]"):
        print(f"[DEBUG] Summarization failed: {summary}")
        return ""
        
    return summary.strip()
