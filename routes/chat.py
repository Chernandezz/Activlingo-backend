from fastapi import APIRouter, HTTPException, Query
from typing import List
from schemas.chat import Chat
from schemas.chat_create import ChatCreate
from services.chat_service import create_chat, get_chats, get_chat_by_id, delete_chat

chat_router = APIRouter()

@chat_router.get("/", response_model=List[Chat])
def get_all_chats(user_id: int = Query(..., description="User ID")):
    return get_chats(user_id)

@chat_router.get("/{chat_id}", response_model=Chat)
def get_chat(chat_id: int):
    chat = get_chat_by_id(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


@chat_router.post("/", response_model=Chat)
def create(user_id: int = Query(...), chat: ChatCreate = ...):
    created = create_chat(user_id, chat)
    if not created:
        raise HTTPException(status_code=500, detail="Error creating chat")
    return created

@chat_router.delete("/{chat_id}")
def delete(chat_id: int):
    success = delete_chat(chat_id)
    if not success:
        raise HTTPException(status_code=404, detail="Chat not found or already deleted")
    return {"success": True, "message": "Chat deleted successfully"}
