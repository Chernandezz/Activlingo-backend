from pydantic import BaseModel
from typing import Literal, List
from datetime import datetime
from uuid import UUID


class MessageCreate(BaseModel):
    user_id: UUID | None = None
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


class MessageResponse(BaseModel):
    message: Message
    human_message: Message
    completed_tasks: List[UUID]
