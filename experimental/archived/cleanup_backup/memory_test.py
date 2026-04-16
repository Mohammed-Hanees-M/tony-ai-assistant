from apps.backend.database.session import SessionLocal
from apps.backend.services.chat_service import process_chat_message

db = SessionLocal()

print("TEST 1")
resp1, cid = process_chat_message(
    db,
    "My favorite color is blue",
    None
)
print("Response:", resp1)
print("CID:", cid)

print("\nTEST 2")
resp2, cid = process_chat_message(
    db,
    "My dog's name is Bruno",
    cid
)
print("Response:", resp2)

print("\nTEST 3")
resp3, cid = process_chat_message(
    db,
    "What is my dog's name and favorite color?",
    cid
)
print("FINAL RESPONSE:", resp3)

db.close()