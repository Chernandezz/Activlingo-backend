from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import UUID


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

    class Config:
        from_attributes = True  # si usas Pydantic v2 (reemplaza orm_mode)
        # orm_mode = True  # solo si sigues con Pydantic v1
