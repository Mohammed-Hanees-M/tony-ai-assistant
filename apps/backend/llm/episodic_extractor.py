import re
import json
from apps.backend.llm.inference import run_llm_inference, generate_embeddings
from apps.backend.llm.router import route_model

EPISODIC_PROMPT = """You are Tony's experience logger. Analyze the conversation turn below.
If a task was completed, a milestone reached, or an important decision made, extract it as an episodic memory.
If nothing significant happened (routine chat), return "NONE".

Fields to extract:
- event_type: (task_completion, milestone, decision, debugging, workflow)
- summary: Short description of the event.
- outcome: Result (success, failure, choice made).
- importance: 1-5 (5 = critical project milestone).
- tags: comma-separated keywords.

Format as JSON if something found, else "NONE".
Example JSON:
{
  "event_type": "debugging",
  "summary": "Fixed connection timeout in Ollama bridge",
  "outcome": "Success, latency reduced by 50ms",
  "importance": 4,
  "tags": "ollama, networking, bugfix"
}
"""

def extract_episodic_memories(user_msg: str, ai_msg: str) -> dict | None:
    """
    Analyzes a conversation turn to detect and extract episodic experiences.
    """
    # Quick filter: don't call LLM for short/trivial chat
    if len(user_msg) < 15 and len(ai_msg) < 15:
        return None

    prompt = [
        {"role": "system", "content": EPISODIC_PROMPT},
        {"role": "user", "content": f"USER: {user_msg}\nAI: {ai_msg}"}
    ]

    model = route_model(user_msg, purpose="extraction")
    response = run_llm_inference(prompt, model)
    
    if "NONE" in response.upper() or "{" not in response:
        return None

    try:
        # Extract JSON block
        match = re.search(r"(\{.*\})", response, re.DOTALL)
        if not match:
            return None
            
        data = json.loads(match.group(1))
        
        # Add embedding for the summary
        vector = generate_embeddings(data["summary"])
        data["embedding"] = json.dumps(vector) if vector else None
        
        return data
    except Exception as e:
        print(f"[DEBUG] Episodic extraction failed to parse: {e}")
        return None
