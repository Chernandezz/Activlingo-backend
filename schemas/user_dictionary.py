from uuid import UUID
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UserDictionaryBase(BaseModel):
    word: str
    meaning: str
    part_of_speech: str
    example: str
    source: Optional[str] = "ChatGPT"
    status: Optional[str] = "passive"
    usage_count: Optional[int] = 1
    last_used_at: Optional[datetime] = None
    usage_context: Optional[str] = "general"
    is_idiomatic: Optional[bool] = False

class UserDictionaryCreate(UserDictionaryBase):
    pass

class UserDictionaryEntry(UserDictionaryBase):
    id: UUID
    user_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
