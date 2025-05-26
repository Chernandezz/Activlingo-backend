import os
from uuid import UUID
from config.supabase_client import supabase
from schemas.user_dictionary import UserDictionaryEntry, UserDictionaryCreate
from ai.dictionary_agent import get_definitions_from_gpt 
from typing import List

# ✅ Agregar una palabra al diccionario del usuario
def add_word(user_id: UUID, entry: UserDictionaryCreate) -> UserDictionaryEntry:
    data = entry.model_dump()
    data["user_id"] = str(user_id)
    response = supabase.table("user_dictionary").insert(data).execute()
    return UserDictionaryEntry(**response.data[0]) if response.data else None

# ✅ Obtener todo el diccionario de un usuario
def get_user_dictionary(user_id: UUID) -> list[UserDictionaryEntry]:
    response = supabase.table("user_dictionary") \
        .select("*") \
        .eq("user_id", str(user_id)) \
        .order("created_at", desc=False) \
        .execute()
    return [UserDictionaryEntry(**d) for d in response.data or []]

# ✅ Eliminar una palabra del diccionario del usuario
def delete_word(word_id: UUID, user_id: UUID) -> bool:
    response = supabase.table("user_dictionary") \
        .delete() \
        .eq("id", str(word_id)) \
        .eq("user_id", str(user_id)) \
        .execute()
    return bool(response.data)

# ✅ Buscar definiciones usando GPT y cachear si no existe
def fetch_definitions_from_api(word: str) -> list[dict]:
    # Buscar en Supabase por palabra ya cacheada (opcional si creas tabla `dictionary_cache`)
    # O simplemente llamar directamente a GPT
    definitions = get_definitions_from_gpt(word)
    return definitions


def save_multiple_definitions(user_id: UUID, word: str, selected_defs: List[UserDictionaryCreate]) -> list[UserDictionaryEntry]:
    entries = []
    for definition in selected_defs:
        payload = {
            "user_id": str(user_id),
            "word": word,
            "meaning": definition.meaning,
            "part_of_speech": definition.part_of_speech,
            "example": definition.example,
            "source": definition.source or "ChatGPT"
        }
        result = supabase.table("user_dictionary").insert(payload).execute()
        if result.data:
            entries.append(UserDictionaryEntry(**result.data[0]))
    return entries