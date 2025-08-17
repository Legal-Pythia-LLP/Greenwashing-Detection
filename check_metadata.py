from app.config import Base
from app.models.chat import Conversation

print("Tables in Base.metadata:")
for table_name, table in Base.metadata.tables.items():
    print(f"- {table_name}")

print("\nIs Conversation registered?", Conversation.__table__ in Base.metadata.tables.values())
