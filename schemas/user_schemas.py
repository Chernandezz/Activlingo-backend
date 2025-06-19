from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime

class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    language: Optional[str] = None
    learning_goal: Optional[str] = None
    difficulty_level: Optional[str] = None
    notifications: Optional[dict] = None

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    avatar_url: str
    created_at: str

class StatsResponse(BaseModel):
    total_conversations: int
    current_streak: int
    longest_streak: int
    total_words_learned: int
    join_date: str
    last_activity: str
    conversations_this_month: int
    words_learned_this_month: int

class AchievementResponse(BaseModel):
    id: str
    title: str
    description: str
    icon: str
    unlocked: bool
    unlocked_at: Optional[str]