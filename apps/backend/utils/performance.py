import hashlib
import json
import time
import threading
from typing import Any, Optional, Dict

class ReasoningCache:
    def __init__(self, filename: str = "cognition_cache.json"):
        self.filename = filename
        self.lock = threading.Lock()
        self.cache: Dict[str, Dict[str, Any]] = self._load_cache()

    def _load_cache(self) -> Dict[str, Dict[str, Any]]:
        try:
            with open(self.filename, 'r') as f:
                return json.load(f)
        except:
            return {}

    def _save_cache(self):
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            pass

    def _generate_key(self, module: str, input_data: Any) -> str:
        data_str = json.dumps(input_data, sort_keys=True, default=str)
        return hashlib.sha256(f"{module}:{data_str}".encode()).hexdigest()

    def get(self, module: str, input_data: Any) -> Optional[Any]:
        key = self._generate_key(module, input_data)
        with self.lock:
            record = self.cache.get(key)
        
        if record:
            expiry = record.get("expiry")
            if expiry and time.time() > expiry:
                with self.lock:
                    if key in self.cache:
                        del self.cache[key]
                self._save_cache()
                return None
            return record.get("data")
        return None

    def set(self, module: str, input_data: Any, result: Any, ttl_seconds: int = 3600):
        key = self._generate_key(module, input_data)
        with self.lock:
            self.cache[key] = {
                "data": result,
                "expiry": time.time() + ttl_seconds,
                "module": module,
                "created_at": time.time()
            }
        self._save_cache()

    def clear_expired(self):
        now = time.time()
        keys_to_delete = [k for k, v in self.cache.items() if v.get("expiry") and now > v.get("expiry")]
        for k in keys_to_delete:
            del self.cache[k]
        if keys_to_delete:
            self._save_cache()

GLOBAL_COGNITION_CACHE = ReasoningCache()
