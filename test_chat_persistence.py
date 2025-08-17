from datetime import datetime
from app.core.store import save_conversation, get_conversation
from app.models.chat import ChatMessage
from app.db import get_db

# Get database session
db = next(get_db())

# Test data
messages = [
    ChatMessage(
        content="Hello",
        sender="user",
        timestamp=datetime.now()
    ),
    ChatMessage(
        content="Hi there",
        sender="assistant",
        timestamp=datetime.now()
    )
]

# Test saving
print("Saving conversation...")
save_conversation(db, "test123", "user1", messages)

# Test retrieving
print("\nRetrieving conversation...")
retrieved = get_conversation(db, "test123")
print("Retrieved messages:", len(retrieved))

# Verify
if retrieved and len(retrieved) == 2:
    print("\n✅ Chat persistence test passed")
else:
    print("\n❌ Chat persistence test failed")
