from config.supabase_client import supabase
from schemas.message import MessageCreate

def add_message(chat_id: str, message: MessageCreate):
    data = message.model_dump()
    data["chat_id"] = chat_id
    response = supabase.table("messages").insert(data).execute()
    return response.data[0] if response.data else None

def get_messages(chat_id: str):
    response = supabase.table("messages").select("*").eq("chat_id", chat_id).order("timestamp", desc=False).execute()
    return response.data or []
