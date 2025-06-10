from uuid import UUID
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# 🟢 Este modelo representa lo que se RECIBE desde el frontend
class UserDictionaryCreate(BaseModel):
    word: str


# 🟡 Este modelo contiene todos los campos comunes
class UserDictionaryBase(BaseModel):
    word: str
    meaning: str
    part_of_speech: str
    example: Optional[str] = ""
    source: Optional[str] = "ChatGPT"
    status: Optional[str] = "passive"
    usage_count: Optional[int] = 0
    last_used_at: Optional[datetime] = None
    usage_context: Optional[str] = "general"
    is_idiomatic: Optional[bool] = False


# 🔵 Este modelo representa una entrada completa devuelta desde Supabase
class UserDictionaryEntry(UserDictionaryBase):
    id: UUID
    user_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
