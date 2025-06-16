# user_dictionary_service.py - OPTIMIZADO SIMPLE SIN REDIS

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from uuid import UUID
import asyncio
import time
from functools import lru_cache

from config.supabase_client import supabase
from services.wordsapi_service import fetch_definitions_from_wordsapi
from ai.dictionary_agent import get_definitions_from_gpt
from schemas.user_dictionary import UserDictionaryCreate, UserDictionaryEntry

CACHE_TTL_DAYS = 300
PROMOTION_THRESHOLD = 3
USER_CACHE_TTL_SECONDS = 300  # 5 minutos

# Cache en memoria simple - perfect para tu escala
user_words_cache = {}
MEMORY_CACHE_TTL = 300  # 5 minutos

def normalize_term(term: str) -> str:
    return term.strip().lower()


# -------------------------
# CACHE DE PALABRAS DEL USUARIO - MEMORIA SIMPLE
# -------------------------

def get_user_dictionary_cached(user_id: str) -> List[UserDictionaryEntry]:
    """Obtener palabras del usuario con cache en memoria"""
    cache_key = f"user_words:{user_id}"
    
    # Verificar cache en memoria
    if cache_key in user_words_cache:
        cached_item = user_words_cache[cache_key]
        if time.time() - cached_item['timestamp'] < MEMORY_CACHE_TTL:
            print(f"✅ Using cached user words for: {user_id}")
            return cached_item['data']
        else:
            # Cache expirado, remover
            del user_words_cache[cache_key]
    
    # Si no hay cache válido, consultar BD
    print(f"🔍 Fetching user words from DB for user: {user_id}")
    response = supabase.table("user_dictionary") \
        .select("*") \
        .eq("user_id", user_id) \
        .order("created_at", desc=True) \
        .execute()
    
    words = [UserDictionaryEntry(**row) for row in response.data or []]
    
    # Guardar en cache
    user_words_cache[cache_key] = {
        'data': words,
        'timestamp': time.time()
    }
    
    # Limpiar cache viejo automáticamente
    clean_expired_cache()
    
    return words


def invalidate_user_cache(user_id: str):
    """Invalidar cache del usuario"""
    cache_key = f"user_words:{user_id}"
    
    if cache_key in user_words_cache:
        del user_words_cache[cache_key]
        print(f"🗑️ Cache invalidated for user: {user_id}")


def clean_expired_cache():
    """Limpiar cache expirado automáticamente"""
    current_time = time.time()
    expired_keys = []
    
    for key, cached_item in user_words_cache.items():
        if current_time - cached_item['timestamp'] > MEMORY_CACHE_TTL:
            expired_keys.append(key)
    
    for key in expired_keys:
        del user_words_cache[key]
    
    if expired_keys:
        print(f"🧹 Cleaned {len(expired_keys)} expired cache entries")


# -------------------------
# FUNCIONES OPTIMIZADAS
# -------------------------

async def add_word(user_id: UUID, entry: UserDictionaryCreate) -> UserDictionaryEntry:
    word = entry.word.strip().lower()

    # Buscar definiciones (usa tu cache de Supabase existente)
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

    # Invalidar cache del usuario
    invalidate_user_cache(str(user_id))

    return UserDictionaryEntry(**response.data[0])


# -------------------------
# DEFINICIONES CON TU CACHÉ EXISTENTE DE SUPABASE (PERFECTO)
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
        print(f"✅ Using Supabase cached definitions for '{term}'")
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
    
    # Tu cache de Supabase existente (¡perfecto!)
    cached = fetch_definitions_from_cache(term_norm)
    if cached is not None:
        return cached

    try:
        print(f"🔍 Fetching definitions for '{term_norm}' from WordsAPI...")
        definitions = await fetch_definitions_from_wordsapi(term_norm)
        print(f"✅ Fetched {len(definitions)} definitions from WordsAPI for '{term_norm}'")
    except Exception as e:
        print(f"❌ WordsAPI failed: {e}")
        definitions = []

    if not definitions:
        print(f"🤖 Falling back to ChatGPT for '{term_norm}'")
        definitions = get_definitions_from_gpt(term_norm)

    if definitions:
        upsert_definitions_to_cache(term_norm, definitions)

    return definitions


# -------------------------
# FUNCIONES EXISTENTES CON CACHE OPTIMIZADO
# -------------------------

def get_user_dictionary(user_id: UUID) -> List[UserDictionaryEntry]:
    """Wrapper para compatibilidad - usa versión cached"""
    return get_user_dictionary_cached(str(user_id))


def get_words_by_status(user_id: UUID, status: str) -> List[UserDictionaryEntry]:
    """Usar cache para filtros también"""
    all_words = get_user_dictionary_cached(str(user_id))
    return [word for word in all_words if word.status == status]


def delete_word(word_id: UUID, user_id: UUID) -> bool:
    res = supabase.table("user_dictionary") \
        .delete() \
        .eq("id", str(word_id)) \
        .eq("user_id", str(user_id)) \
        .execute()

    success = bool(res.data)
    if success:
        invalidate_user_cache(str(user_id))
    
    return success


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
    
    # Invalidar cache después de update
    invalidate_user_cache(str(user_id))


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
        
        # Invalidar cache después de promoción
        invalidate_user_cache(str(user_id))


def update_word_usage(user_id: UUID, text: str):
    """Optimizada para usar cache"""
    words_in_text = set(w.lower().strip(".,!?") for w in text.split())
    
    # Usar cache en lugar de consulta BD
    user_words = get_user_dictionary_cached(str(user_id))
    
    updates = []
    for word in user_words:
        if word.word.lower() in words_in_text:
            updates.append({
                "id": str(word.id),
                "usage_count": word.usage_count + 1,
                "last_used_at": datetime.utcnow().isoformat()
            })

    # Batch update
    if updates:
        for u in updates:
            supabase.table("user_dictionary") \
                .update({
                    "usage_count": u["usage_count"],
                    "last_used_at": u["last_used_at"]
                }) \
                .eq("id", str(u["id"])) \
                .execute()
        
        # Invalidar cache una sola vez después de todos los updates
        invalidate_user_cache(str(user_id))


def suggest_similar_words(term: str, limit: int = 20) -> List[Dict]:
    res = supabase.table("dictionary_cache") \
        .select("word, definitions") \
        .ilike("word", f"{term}%") \
        .limit(limit) \
        .execute()

    return res.data or []


# -------------------------
# UTILIDADES DE CACHE
# -------------------------

def get_cache_stats() -> Dict:
    """Estadísticas del cache para monitoring"""
    current_time = time.time()
    valid_entries = 0
    expired_entries = 0
    
    for cached_item in user_words_cache.values():
        if current_time - cached_item['timestamp'] < MEMORY_CACHE_TTL:
            valid_entries += 1
        else:
            expired_entries += 1
    
    return {
        "cache_type": "memory_only",
        "total_entries": len(user_words_cache),
        "valid_entries": valid_entries,
        "expired_entries": expired_entries,
        "cache_keys": list(user_words_cache.keys())
    }


def clear_all_caches():
    """Limpiar todos los caches - útil para desarrollo"""
    global user_words_cache
    user_words_cache = {}
    print("🗑️ All user caches cleared")

