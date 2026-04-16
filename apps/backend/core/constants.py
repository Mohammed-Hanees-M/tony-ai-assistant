# Model Collection
MODEL_TIER_1 = "phi3:latest"   # Lightweight, fast, low reasoning
MODEL_TIER_2 = "llama3:latest" # High reasoning, factual, technical

# Default Role Assignments
DEFAULT_CHAT_MODEL = MODEL_TIER_2
DEFAULT_SUMMARIZATION_MODEL = MODEL_TIER_2
DEFAULT_EXTRACTION_MODEL = MODEL_TIER_2
DEFAULT_EMBEDDING_MODEL = "nomic-embed-text"

# Settings Keys
SETTING_MODEL_SELECTION = "model_selection"
