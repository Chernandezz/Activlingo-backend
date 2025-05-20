from fastapi import APIRouter, HTTPException
from schemas.message import Message
from schemas.MessageCreate import MessageCreate
from services.message_service import get_messages_by_chat_id, create_message

message_router = APIRouter()

@message_router.get("/by_chat/{chat_id}", response_model=list[Message])
def get_messages(chat_id: str):
    return get_messages_by_chat_id(chat_id)

@message_router.post("/", response_model=Message)
def create(message: MessageCreate):
    return create_message(message)
