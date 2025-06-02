from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class Task(BaseModel):
    id: UUID
    chat_id: UUID
    description: str
    completed: bool
    type: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
