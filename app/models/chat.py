from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy import Column, String, Text, DateTime
from app.models.base import Base

class ChatMessage(BaseModel):
    content: str
    sender: str  # "user" or "assistant"
    timestamp: datetime

    def dict(self, **kwargs):
        data = super().dict(**kwargs)
        data['timestamp'] = self.timestamp.isoformat()
        return data

# Defines the base structure for user-system conversations
class ChatBaseMessage(BaseModel):
    message: str
    session_id: str
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    message_history: List[ChatMessage] = []

# Database model for storing conversations
class Conversation(Base):
    __tablename__ = "conversations"

    conversation_id = Column(String(255), primary_key=True)
    user_id = Column(String(255))
    messages = Column(Text)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
