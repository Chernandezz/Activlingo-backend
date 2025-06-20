from fastapi import APIRouter, HTTPException, Depends
from typing import List
from uuid import UUID
from schemas.chat import Chat
from schemas.chat_create import ChatCreate
from services.chat_service import create_chat, get_chats, get_chat_by_id, delete_chat
from dependencies.auth import get_current_user

chat_router = APIRouter()

@chat_router.get("/", response_model=List[Chat])
def get_all_chats(user_id: UUID = Depends(get_current_user)):
    return get_chats(user_id)


@chat_router.get("/{chat_id}", response_model=Chat)
def get_chat(chat_id: UUID):
    chat = get_chat_by_id(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat

@chat_router.post("/", response_model=Chat)
def create(chat: ChatCreate, user_id: str = Depends(get_current_user)):
    created = create_chat(user_id, chat)
    if not created:
        raise HTTPException(status_code=500, detail="Error creating chat")
    return created

@chat_router.delete("/{chat_id}")
def delete(chat_id: UUID):
    success = delete_chat(chat_id)
    if not success:
        raise HTTPException(status_code=404, detail="Chat not found or already deleted")
    return {"success": True, "message": "Chat deleted successfully"}
