from config.supabase_client import supabase
from schemas.message import Message, MessageCreate

def create_message(message_data: MessageCreate) -> Message | None:
    data = message_data.model_dump()
    response = supabase.table("messages").insert(data).execute()
    return response.data[0] if response.data else None

def get_messages(chat_id: int) -> list[Message]:
    response = supabase.table("messages") \
        .select("*") \
        .eq("chat_id", chat_id) \
        .order("timestamp") \
        .execute()
    return response.data or []

def delete_message(message_id: int) -> bool:
    response = supabase.table("messages").delete().eq("id", message_id).execute()
    return isinstance(response.data, list) and len(response.data) > 0
