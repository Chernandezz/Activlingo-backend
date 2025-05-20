from pydantic import BaseModel
from typing import Literal
from datetime import datetime

class MessageCreate(BaseModel):
    sender: Literal['user', 'bot']
    content: str

class Message(BaseModel):
    id: str
    chat_id: str
    sender: str
    content: str
    timestamp: datetime

    class Config:
        orm_mode = True