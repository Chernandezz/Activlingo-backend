from config.supabase_client import supabase
from schemas.user_dictionary import UserDictionaryEntry, UserDictionaryCreate
from uuid import UUID

def add_word(user_id: UUID, entry: UserDictionaryCreate) -> UserDictionaryEntry:
    data = entry.model_dump()
    data["user_id"] = str(user_id)
    response = supabase.table("user_dictionary").insert(data).execute()
    return UserDictionaryEntry(**response.data[0]) if response.data else None

def get_user_dictionary(user_id: UUID) -> list[UserDictionaryEntry]:
    response = supabase.table("user_dictionary").select("*").eq("user_id", str(user_id)).order("created_at", desc=False).execute()
    return [UserDictionaryEntry(**d) for d in response.data or []]

def delete_word(word_id: UUID, user_id: UUID) -> bool:
    response = supabase.table("user_dictionary").delete().eq("id", str(word_id)).eq("user_id", str(user_id)).execute()
    return bool(response.data)
