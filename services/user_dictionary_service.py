from typing import List, Dict, Optional
from datetime import datetime, timedelta
from uuid import UUID
import asyncio

from config.supabase_client import supabase
from services.wordsapi_service import fetch_definitions_from_wordsapi
from ai.dictionary_agent import get_definitions_from_gpt
from schemas.user_dictionary import UserDictionaryCreate, UserDictionaryEntry

CACHE_TTL_DAYS = 300
PROMOTION_THRESHOLD = 3  # Número de usos para promover de pasiva a activa


def normalize_term(term: str) -> str:
    return term.strip().lower()


# -------------------------
# GUARDAR PALABRA NUEVA
# -------------------------
async def add_word(user_id: UUID, entry: UserDictionaryCreate) -> UserDictionaryEntry:
    word = entry.word.strip().lower()

    # Buscar definiciones
    definitions = await fetch_definitions(word)
    if not definitions:
        raise Exception(f"No definitions found for word: {word}")

    first = definitions[0]

    # Verificar duplicado exacto
    existing = supabase.table("user_dictionary") \
        .select("id") \
        .eq("user_id", str(user_id)) \
        .eq("word", word) \
        .eq("meaning", first["meaning"]) \
        .execute()

    if existing.data:
        raise Exception("Duplicate word with same meaning")

    payload = {
        "user_id": str(user_id),
        "word": word,
        "meaning": first["meaning"],
        "part_of_speech": first.get("part_of_speech", "unknown"),
        "example": first.get("example", ""),
        "source": first.get("source", "unknown"),
        "status": "passive",
        "usage_count": 0,
        "usage_context": first.get("usage_context", "general"),
        "is_idiomatic": first.get("is_idiomatic", False),
    }

    response = supabase.table("user_dictionary").insert(payload).execute()

    if not response.data:
        raise Exception("Failed to insert word")

    return UserDictionaryEntry(**response.data[0])


# -------------------------
# DEFINICIONES CON CACHÉ
# -------------------------
def fetch_definitions_from_cache(term: str) -> Optional[List[Dict]]:
    res = supabase.table("dictionary_cache") \
        .select("definitions, last_updated") \
        .eq("word", term) \
        .limit(1) \
        .execute()

    if not res.data:
        return None

    row = res.data[0]

    fetched_at = datetime.fromisoformat(row["last_updated"])
    if fetched_at >= datetime.utcnow() - timedelta(days=CACHE_TTL_DAYS):
        print(f"✅ Using cached definitions for '{term}'")
        return row["definitions"]

    print(f"⚠️ Cache expired for '{term}'")
    supabase.table("dictionary_cache").delete().eq("word", term).execute()
    return None




def upsert_definitions_to_cache(term: str, definitions: List[Dict]) -> None:
    now_iso = datetime.utcnow().isoformat()
    supabase.table("dictionary_cache").upsert({
        "word": term,
        "definitions": definitions,
        "last_updated": now_iso
    }, on_conflict="word").execute()


async def fetch_definitions(term: str) -> List[Dict]:
    term_norm = normalize_term(term)
    cached = fetch_definitions_from_cache(term_norm)
    if cached is not None:
        return cached

    try:
        print(f"Fetching definitions for '{term_norm}' from WordsAPI...")
        definitions = await fetch_definitions_from_wordsapi(term_norm)
        print(f"Fetched {len(definitions)} definitions from WordsAPI for '{term_norm}'")
    except Exception:
        definitions = []

    if not definitions:
        definitions = get_definitions_from_gpt(term_norm)

    upsert_definitions_to_cache(term_norm, definitions)
    return definitions


# -------------------------
# SUGERENCIAS
# -------------------------
def suggest_similar_words(term: str, limit: int = 20) -> List[Dict]:
    res = supabase.table("dictionary_cache") \
        .select("word, type") \
        .ilike("word", f"{term}%") \
        .limit(limit) \
        .execute()

    return res.data or []


# -------------------------
# LISTAR PALABRAS DEL USUARIO
# -------------------------
def get_user_dictionary(user_id: UUID) -> List[UserDictionaryEntry]:
    response = supabase.table("user_dictionary") \
        .select("*") \
        .eq("user_id", str(user_id)) \
        .order("created_at", desc=True) \
        .execute()

    return [UserDictionaryEntry(**row) for row in response.data or []]


# -------------------------
# FILTRAR POR STATUS
# -------------------------
def get_words_by_status(user_id: UUID, status: str) -> List[UserDictionaryEntry]:
    res = supabase.table("user_dictionary") \
        .select("*") \
        .eq("user_id", str(user_id)) \
        .eq("status", status) \
        .order("last_used_at", desc=True) \
        .execute()

    return [UserDictionaryEntry(**row) for row in res.data or []]


# -------------------------
# ELIMINAR PALABRA
# -------------------------
def delete_word(word_id: UUID, user_id: UUID) -> bool:
    res = supabase.table("user_dictionary") \
        .delete() \
        .eq("id", str(word_id)) \
        .eq("user_id", str(user_id)) \
        .execute()

    return bool(res.data)


# -------------------------
# REGISTRAR USO
# -------------------------
def log_word_usage(user_id: UUID, word_id: UUID, context: str = "general"):
    now = datetime.utcnow().isoformat()
    res = supabase.table("user_dictionary") \
        .select("usage_count") \
        .eq("user_id", str(user_id)) \
        .eq("id", str(word_id)) \
        .single() \
        .execute()

    if not res.data:
        return

    usage_count = res.data["usage_count"] + 1

    supabase.table("user_dictionary") \
        .update({
            "usage_count": usage_count,
            "last_used_at": now,
        }) \
        .eq("id", str(word_id)) \
        .execute()


# -------------------------
# PROMOCIONAR SI ES NECESARIO
# -------------------------
def check_and_promote_word(user_id: UUID, word_id: UUID):
    res = supabase.table("user_dictionary") \
        .select("usage_count", "status") \
        .eq("user_id", str(user_id)) \
        .eq("id", str(word_id)) \
        .single() \
        .execute()

    if not res.data:
        return

    usage_count = res.data["usage_count"]
    status = res.data["status"]

    if status == "passive" and usage_count >= PROMOTION_THRESHOLD:
        supabase.table("user_dictionary") \
            .update({"status": "active"}) \
            .eq("id", str(word_id)) \
            .execute()


def update_word_usage(user_id: UUID, text: str):
    """
    Extrae palabras del texto, actualiza usage_count y last_used_at de las que ya están en el diccionario del usuario.
    """
    words_in_text = set(w.lower().strip(".,!?") for w in text.split())

    res = supabase.table("user_dictionary") \
        .select("id, word, usage_count") \
        .eq("user_id", str(user_id)) \
        .execute()

    if not res.data:
        return

    updates = []
    for row in res.data:
        if row["word"].lower() in words_in_text:
            updates.append({
                "id": row["id"],
                "usage_count": row["usage_count"] + 1,
                "last_used_at": datetime.utcnow().isoformat()
            })

    for u in updates:
        supabase.table("user_dictionary") \
            .update({
                "usage_count": u["usage_count"],
                "last_used_at": u["last_used_at"]
            }) \
            .eq("id", str(u["id"])) \
            .execute()
