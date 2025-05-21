from config.supabase_client import supabase
from schemas.message import Message, MessageCreate
from postgrest.exceptions import APIError

def create_message(chat_id: int, sender: str, content: str) -> Message | None:
    data = {
        "chat_id": chat_id,
        "sender": sender,
        "content": content
    }

    try:
        response = supabase.table("messages").insert(data).execute()
        return response.data[0] if response.data else None
    except APIError as e:
        print("Supabase insert error:", str(e))
        return None

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
