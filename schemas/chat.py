from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import UUID

from schemas.message import Message


class TaskItem(BaseModel):
    id: UUID
    description: str
    completed: bool


class ChatCreate(BaseModel):
    title: str
    language: Optional[str] = "en"
    level: Optional[str] = "beginner"
    role: str
    context: str
    tasks: Optional[List[str]] = None  # Esto se mantiene si aún solo se envían strings al crear


class Chat(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    language: str
    level: str
    created_at: datetime
    initial_message: Optional[str] = None
    tasks: List[TaskItem] = []
    messages: Optional[List[Message]] = [] 
    updated_at: datetime

    class Config:
        from_attributes = True 
