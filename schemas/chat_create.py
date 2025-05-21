from pydantic import BaseModel
from typing import Optional

class ChatCreate(BaseModel):
    title: str
    language: Optional[str] = "en"
    level: Optional[str] = "beginner"
    role: str
    context: str