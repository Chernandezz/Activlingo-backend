from pydantic import BaseModel
from typing import Literal
from datetime import datetime

class MessageCreate(BaseModel):
    chat_id: int
    sender: Literal["user", "bot"]
    content: str

class Message(BaseModel):
    id: int
    chat_id: int
    sender: Literal["user", "bot"]
    content: str
    timestamp: datetime

    class Config:
        from_attributes = True