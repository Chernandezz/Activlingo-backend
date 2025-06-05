from pydantic import BaseModel
from typing import Literal
from datetime import datetime
from uuid import UUID

class MessageAnalysis(BaseModel):
    id: UUID
    message_id: UUID
    category: str
    mistake: str
    issue: str
    suggestion: str
    explanation: str
    created_at: datetime

    class Config:
        from_attributes = True
