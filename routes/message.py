from fastapi import APIRouter, HTTPException, Query
from typing import List
from schemas.message import Message, MessageCreate
from services.message_service import create_message, get_messages, delete_message, handle_human_message

message_router = APIRouter()

@message_router.get("/", response_model=List[Message])
def list_messages(chat_id: int = Query(...)):
    return get_messages(chat_id)

@message_router.post("/", response_model=Message)
def create(msg: MessageCreate):
    created = handle_human_message(msg)
    
    if not created:
        raise HTTPException(status_code=500, detail="Error creating message")
    return created

@message_router.delete("/{message_id}")
def delete(message_id: int):
    success = delete_message(message_id)
    if not success:
        raise HTTPException(status_code=404, detail="Message not found or already deleted")
    return {"success": True, "message": "Message deleted successfully"}
