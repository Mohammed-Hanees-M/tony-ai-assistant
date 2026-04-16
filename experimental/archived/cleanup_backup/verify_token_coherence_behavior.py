import time
from apps.backend.database.session import SessionLocal
from apps.backend.services.chat_service import process_chat_message

db = SessionLocal()

print("=== TOKEN COHERENCE BEHAVIOR TEST ===")

# Create conversation
response, cid = process_chat_message(
    db,
    "My favorite framework is FastAPI because it is modern and fast.",
    None
)

print(f"CID: {cid}")
print(f"Tony: {response}")

# Add long filler messages to force token trimming
for i in range(10):
    print(f"\n[Test] Adding filler message {i+1}/10...")
    long_text = f"FILLER MESSAGE {i} " + ("X" * 1000)
    process_chat_message(db, long_text, cid)
    time.sleep(2) # Stabilize Ollama

# Ask about remembered fact
response, cid = process_chat_message(
    db,
    "Why do I like FastAPI?",
    cid
)

print("\nFINAL TEST RESPONSE:")
print(response)

db.close()