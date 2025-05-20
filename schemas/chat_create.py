from pydantic import BaseModel
from typing import Optional

class ChatCreate(BaseModel):
    title: str
    language: str = "en"
    level: str = "beginner"
