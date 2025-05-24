from fastapi import APIRouter, HTTPException
from schemas.chat_analysis import MessageAnalysis
from services.analysis_service import get_analysis_by_chat_id
from typing import List

analysis_router = APIRouter()

@analysis_router.get("/{chat_id}", response_model=List[MessageAnalysis])
def get_chat_analysis_by_chat(chat_id: int):
    return get_analysis_by_chat_id(chat_id)
