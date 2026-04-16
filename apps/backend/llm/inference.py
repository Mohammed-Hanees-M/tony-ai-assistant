import requests
import json
import time
from typing import List, Dict, Generator, Optional

TOTAL_LLM_CALLS = 0

def get_llm_call_count():
    return TOTAL_LLM_CALLS

def reset_llm_call_count():
    global TOTAL_LLM_CALLS
    TOTAL_LLM_CALLS = 0

class LLMProvider:
    def chat(self, messages: List[Dict[str, str]], model: str) -> str:
        raise NotImplementedError
    
    def stream(self, messages: List[Dict[str, str]], model: str) -> Generator[str, None, None]:
        raise NotImplementedError

class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url

    def chat(self, messages: List[Dict[str, str]], model: str) -> str:
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": model,
            "messages": messages,
            "stream": False
        }
        
        try:
            response = requests.post(url, json=payload, timeout=120)
            if response.status_code != 200:
                return f"[Error] Ollama returned status {response.status_code}: {response.text}"
            
            data = response.json()
            return data["message"]["content"].strip()
        except requests.exceptions.ConnectionError:
            return "[Error] Ollama connection refused. Ensure Ollama is running at http://localhost:11434"
        except Exception as e:
            return f"[Error] Ollama inference failed: {str(e)}"

    def stream(self, messages: List[Dict[str, str]], model: str) -> Generator[str, None, None]:
        url = f"{self.base_url}/api/chat"
        payload = {"model": model, "messages": messages, "stream": True}
        
        try:
            response = requests.post(url, json=payload, stream=True, timeout=120)
            if response.status_code != 200:
                yield f"[Error] Ollama error: {response.text}"
                return

            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line)
                    if "message" in chunk:
                        yield chunk["message"]["content"]
                    if chunk.get("done"):
                        break
        except requests.exceptions.ConnectionError:
            yield "[Error] Ollama connection refused."
        except Exception as e:
            yield f"[Error] {str(e)}"

class GeminiProvider(LLMProvider):
    def __init__(self, api_key: Optional[str] = None):
        import os
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")

    def chat(self, messages: List[Dict[str, str]], model: str) -> str:
        if not self.api_key:
            return "[Error] Gemini API key not found. Please set GOOGLE_API_KEY in your environment."
        
        # Default to gemini-2.0-flash if model name is generic
        gemini_model = "gemini-2.0-flash"
        if "flash" in model.lower():
            gemini_model = "gemini-2.0-flash"
        elif "pro" in model.lower():
            gemini_model = "gemini-1.5-pro"

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={self.api_key}"
        
        # Convert OpenAI-style messages to Gemini style
        contents = []
        system_instruction = ""
        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            else:
                role = "user" if msg["role"] == "user" else "model"
                contents.append({
                    "role": role,
                    "parts": [{"text": msg["content"]}]
                })
        
        payload = {
            "contents": contents
        }
        if system_instruction:
            payload["system_instruction"] = {
                "parts": [{"text": system_instruction}]
            }

        try:
            response = requests.post(url, json=payload, timeout=60)
            if response.status_code != 200:
                return f"[Error] Gemini API returned {response.status_code}: {response.text}"
            
            data = response.json()
            # Extract content from Gemini response structure
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            return f"[Error] Gemini inference failed: {str(e)}"

    def stream(self, messages: List[Dict[str, str]], model: str) -> Generator[str, None, None]:
        # Simple non-streaming fallback for now or implement streamGenerateContent
        yield self.chat(messages, model)

def get_provider(model: str) -> LLMProvider:
    if "gemini" in model.lower():
        return GeminiProvider()
    return OllamaProvider()

def run_llm_inference(messages: List[Dict[str, str]], model: str, depth: int = 0) -> str:
    """Sends structured messages to the appropriate LLM provider with automatic fallback and timeout."""
    global TOTAL_LLM_CALLS
    TOTAL_LLM_CALLS += 1
    
    from apps.backend.core.constants import MODEL_TIER_1
    
    print(f"[DEBUG] [INFERENCE] Provider routing for model: {model} (Attempt {depth + 1})")
    provider = get_provider(model)
    
    # Fast Fallback Logic: If primay model (llama3) takes > 3s, abort and use TIER_1
    start_time = time.time()
    result = "[Error] Timeout"
    
    try:
        # We wrap the provider call. Note: requests timeout is handled at provider level,
        # but here we enforce a stricter 3s 'patience' for the primary attempt.
        timeout_val = 3.0 if depth == 0 and model != MODEL_TIER_1 else 120.0
        
        # Note: requests timeout in OllamaProvider/GeminiProvider is fixed. 
        # Here we rely on the provider's internal timeout or just check elapsed after.
        # To truly interrupt, we'd need threading. For now, we'll enforce it by passing 
        # timeout to the provider if possible, or checking if duration > timeout.
        
        # Let's actually pass a timeout to the provider. 
        # I will modify the provider classes too.
        result = provider.chat(messages, model)
    except Exception as e:
        result = f"[Error] {str(e)}"
        
    duration = time.time() - start_time
    
    # CRITICAL: Fast Fallback for llama3/slow models
    if (is_error_response(result) or duration > 3.0) and depth == 0 and model != MODEL_TIER_1:
        reason = "Timeout (>3s)" if duration > 3.0 else "Error"
        print(f"[DEBUG] [INFERENCE] {reason} on {model}. Triggering FAST_FALLBACK to {MODEL_TIER_1}...")
        return run_llm_inference(messages, MODEL_TIER_1, depth=depth + 1)
        
    if is_error_response(result):
        print(f"[DEBUG] [INFERENCE] FAILED in {duration:.2f}s: {result}")
        return result
    else:
        print(f"[DEBUG] [INFERENCE] SUCCESS in {duration:.2f}s")
        
    return result

def run_llm_inference_stream(messages: List[Dict[str, str]], model: str):
    """Streams tokens from the appropriate LLM provider."""
    provider = get_provider(model)
    return provider.stream(messages, model)

def generate_embeddings(text: str, model: str = "nomic-embed-text") -> List[float]:
    """Generates a vector embedding for the provided text using Ollama."""
    url = "http://localhost:11434/api/embeddings"
    payload = {"model": model, "prompt": text}
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code != 200:
            return []
        return response.json()["embedding"]
    except Exception:
        return []

def is_error_response(response: str) -> bool:
    """Centralized check to determine if an inference response failed."""
    return isinstance(response, str) and response.startswith("[Error]")