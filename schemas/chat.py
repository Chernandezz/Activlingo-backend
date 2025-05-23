from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ChatCreate(BaseModel):
    title: str
    language: Optional[str] = 'en'
    level: Optional[str] = 'beginner'

class Chat(BaseModel):
    id: int
    user_id: int
    title: str
    language: str
    level: str
    created_at: datetime
    initial_message: Optional[str] = None

    class Config:
        orm_mode = True