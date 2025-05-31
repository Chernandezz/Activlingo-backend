from uuid import UUID
from datetime import datetime, timedelta
from typing import List
from ai.dictionary_agent import get_definitions_from_gpt
from config.supabase_client import supabase
from schemas.user_dictionary import UserDictionaryEntry, UserDictionaryCreate


# En user_service/dictionary.py

COMMON_WORDS = {
    'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'I', 
    'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
    'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she',
    'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their', 'what',
    'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go', 'me',
    'when', 'make', 'can', 'like', 'time', 'no', 'just', 'him', 'know', 'take',
    'people', 'into', 'year', 'your', 'good', 'some', 'could', 'them', 'see',
    'other', 'than', 'then', 'now', 'look', 'only', 'come', 'its', 'over',
    'think', 'also', 'back', 'after', 'use', 'two', 'how', 'our', 'work',
    'first', 'well', 'way', 'even', 'new', 'want', 'because', 'any', 'these',
    'give', 'day', 'most', 'us', 'is', 'are', 'was', 'were'
}
import re
from typing import Set

def extract_relevant_words(text: str) -> Set[str]:
    # Eliminar puntuación y convertir a minúsculas
    words = re.findall(r"\b[\w'-]+\b", text.lower())
    # Filtrar palabras comunes y muy cortas
    return {
        word for word in words 
        if word not in COMMON_WORDS 
        and len(word) > 2 
        and not word.isnumeric()
    }

# En user_service/dictionary.py

def update_word_usage(user_id: UUID, message: str) -> None:
    # Extraer palabras relevantes del mensaje
    words = extract_relevant_words(message)
    if not words:
        return
    
    # Obtener todas las palabras del usuario que coincidan
    response = supabase.table("user_dictionary") \
        .select("id, word") \
        .eq("user_id", str(user_id)) \
        .in_("word", list(words)) \
        .execute()
    
    existing_words = {entry["word"].lower(): entry["id"] for entry in response.data}
    
    # Actualizar contador para palabras existentes
    for word, word_id in existing_words.items():
        log_word_usage(user_id, word_id)
        check_and_promote_word(user_id, word_id)
    
    # Identificar palabras nuevas que no están en el diccionario del usuario
    new_words = [w for w in words if w not in existing_words]
    
    # Agregar palabras nuevas automáticamente con definición básica
    for word in new_words:
        try:
            # Buscar en caché primero
            cached_defs = search_word_in_cache(word)
            if not cached_defs:
                cached_defs = fetch_and_cache_definitions(word)
            
            if cached_defs:
                # Tomar la primera definición como valor por defecto
                first_def = cached_defs[0]
                new_entry = UserDictionaryCreate(
                    word=word,
                    meaning=first_def.get("definition", f"Definition of {word}"),
                    part_of_speech=first_def.get("part_of_speech", "noun"),
                    example=first_def.get("example", ""),
                    source="auto-added"
                )
                added_word = add_word(user_id, new_entry)
                if added_word:
                    log_word_usage(user_id, added_word.id)
        except Exception as e:
            print(f"⚠️ Could not auto-add word {word}: {str(e)}")


def add_word(user_id: UUID, entry: UserDictionaryCreate) -> UserDictionaryEntry:
    # Verificar si ya existe esa palabra con el mismo significado
    existing = supabase.table("user_dictionary") \
        .select("id") \
        .eq("user_id", str(user_id)) \
        .eq("word", entry.word.strip()) \
        .eq("meaning", entry.meaning.strip()) \
        .execute()

    if existing.data:
        raise Exception("Ya existe esta palabra con el mismo significado")

    data = entry.model_dump()
    data["user_id"] = str(user_id)

    response = supabase.table("user_dictionary").insert(data).execute()
    return UserDictionaryEntry(**response.data[0]) if response.data else None


# 📄 Listar todas las palabras
def get_user_dictionary(user_id: UUID) -> List[UserDictionaryEntry]:
    response = supabase.table("user_dictionary") \
        .select("*") \
        .eq("user_id", str(user_id)) \
        .order("created_at", desc=False) \
        .execute()
    return [UserDictionaryEntry(**d) for d in response.data or []]


# ❌ Eliminar palabra
def delete_word(word_id: UUID, user_id: UUID) -> bool:
    response = supabase.table("user_dictionary") \
        .delete() \
        .eq("id", str(word_id)) \
        .eq("user_id", str(user_id)) \
        .execute()
    return bool(response.data)


# 🔎 Buscar en cache
def search_word_in_cache(word: str) -> list[dict]:
    response = supabase.table("dictionary_cache") \
        .select("definitions") \
        .eq("word", word.lower()) \
        .execute()
    return response.data[0]["definitions"] if response.data else []


# 🔁 Buscar usando GPT y cachear


def fetch_definitions_from_api(word: str) -> list[dict]:
    definitions = get_definitions_from_gpt(word)
    return definitions


# 📥 Guardar múltiples definiciones
def save_multiple_definitions(user_id: UUID, word: str, selected_defs: List[UserDictionaryCreate]) -> List[UserDictionaryEntry]:
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


# ✅ Filtrar palabras por estado
def get_words_by_status(user_id: UUID, status: str) -> List[UserDictionaryEntry]:
    response = supabase.table("user_dictionary") \
        .select("*") \
        .eq("user_id", str(user_id)) \
        .eq("status", status) \
        .order("created_at", desc=False) \
        .execute()
    return [UserDictionaryEntry(**d) for d in response.data or []]


def fetch_and_cache_definitions(word: str):
    cached = search_word_in_cache(word)
    if cached:
        return cached
    
    definitions = get_definitions_from_gpt(word)
    supabase.table("dictionary_cache").insert({"word": word.lower(), "definitions": definitions}).execute()
    return definitions


# 🧠 Registrar uso de palabra
def log_word_usage(user_id: UUID, word_id: UUID, context: str = "chat") -> None:
    # Obtener uso actual
    current_data = supabase.table("user_dictionary") \
        .select("usage_count") \
        .eq("user_id", str(user_id)) \
        .eq("id", str(word_id)) \
        .single() \
        .execute()

    current_usage = current_data.data["usage_count"] if current_data.data else 0

    # Actualizar valores
    supabase.table("user_word_logs").insert({
        "user_id": str(user_id),
        "word_id": str(word_id),
        "context": context
    }).execute()

    supabase.table("user_dictionary") \
        .update({
            "usage_count": current_usage + 1,
            "last_used_at": datetime.utcnow().isoformat(),
            "usage_context": context
        }) \
        .eq("user_id", str(user_id)) \
        .eq("id", str(word_id)) \
        .execute()


# 📈 Promover palabra si se ha usado suficiente
def check_and_promote_word(user_id: UUID, word_id: UUID, threshold: int = 20):
    word = supabase.table("user_dictionary") \
        .select("status, usage_count") \
        .eq("id", str(word_id)) \
        .eq("user_id", str(user_id)) \
        .eq("status", "passive") \
        .execute().data[0]
    
    if word and word["usage_count"] >= threshold:
        supabase.table("user_dictionary") \
            .update({"status": "active"}) \
            .eq("id", str(word_id)) \
            .execute()