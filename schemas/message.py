from pydantic import BaseModel
from typing import Literal
from datetime import datetime
from uuid import UUID

class MessageCreate(BaseModel):
    user_id: UUID
    chat_id: UUID
    sender: Literal["human", "ai", "system"]
    content: str

class Message(BaseModel):
    id: UUID
    chat_id: UUID
    sender: Literal["human", "ai", "system"]
    content: str
    timestamp: datetime

    class Config:
        from_attributes = True
