from pydantic import BaseModel
from typing import Literal
from datetime import datetime

class MessageAnalysis(BaseModel):
    id: int
    message_id: int
    category: str
    mistake: str
    issue: str
    suggestion: str
    explanation: str
    created_at: datetime

    class Config:
        orm_mode = True
