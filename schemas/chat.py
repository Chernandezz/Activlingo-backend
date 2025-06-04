from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

class ChatCreate(BaseModel):
    title: str
    language: Optional[str] = "en"
    level: Optional[str] = "beginner"
    role: str
    context: str

class Chat(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    language: str
    level: str
    created_at: datetime
    initial_message: Optional[str] = None

    class Config:
        from_attributes = True
