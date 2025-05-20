from config.supabase_client import supabase
from schemas.chat import Chat
from schemas.chat_create import ChatCreate
from postgrest.exceptions import APIError


def create_chat(user_id: int, chat_data: ChatCreate) -> Chat | None:
    data = chat_data.model_dump()
    data["user_id"] = user_id

    try:
      response = supabase.table("chats").insert(data).execute()
      return response.data[0] if response.data else None
    except APIError as e:
      if "23503" in str(e):
        return None
      raise e 

def get_chats(user_id: int) -> list[Chat]:
    response = supabase.table("chats").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
    return response.data or []

def get_chat_by_id(chat_id: int) -> Chat | None:
    response = supabase.table("chats").select("*").eq("id", chat_id).limit(1).execute()
    return response.data[0] if response.data else None



def delete_chat(chat_id: int) -> bool:
    response = supabase.table("chats").delete().eq("id", chat_id).execute()
    return bool(response.data)

