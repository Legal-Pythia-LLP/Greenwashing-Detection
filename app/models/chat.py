from pydantic import BaseModel

# Define the basic structure for user and system messages
class ChatBaseMessage(BaseModel):
    message: str
    session_id: str
