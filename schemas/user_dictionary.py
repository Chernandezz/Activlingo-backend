from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

class UserDictionaryEntry(BaseModel):
    id: UUID
    user_id: UUID
    word: str
    meaning: str
    part_of_speech: Optional[str]
    source: Optional[str]
    example: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class UserDictionaryCreate(BaseModel):
    word: str
    meaning: str
    part_of_speech: Optional[str] = None
    source: Optional[str] = None
    example: Optional[str] = None
