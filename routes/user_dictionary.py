from fastapi import APIRouter, HTTPException, Query, Body
from uuid import UUID
from typing import List, Dict, Optional
from datetime import datetime, timedelta

import supabase

from schemas.user_dictionary import UserDictionaryCreate, UserDictionaryEntry
from services.user_dictionary_service import (
    add_word,
    fetch_and_cache_definitions,
    get_user_dictionary,
    delete_word,
    fetch_definitions_from_api,
    save_multiple_definitions,
    search_word_in_cache,
    log_word_usage,
    check_and_promote_word,
    get_words_by_status
)

user_dictionary_router = APIRouter()


# ✅ Guardar una palabra individual
@user_dictionary_router.post("/", response_model=UserDictionaryEntry)
def save_word(user_id: UUID = Query(...), entry: UserDictionaryCreate = ...):
    return add_word(user_id, entry)


# ✅ Listar todas las palabras del usuario
@user_dictionary_router.get("/", response_model=List[UserDictionaryEntry])
def list_words(
    user_id: UUID = Query(...),
    skip: int = 0,
    limit: int = 50
):
    return get_user_dictionary(user_id)[skip:skip + limit]


# ✅ Eliminar una palabra
@user_dictionary_router.delete("/{word_id}")
def remove_word(word_id: UUID, user_id: UUID = Query(...)):
    success = delete_word(word_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Word not found or already deleted")
    return {"success": True, "message": "Word deleted successfully"}


@user_dictionary_router.get("/search", response_model=List[dict])
def search_definitions(word: str = Query(..., min_length=1)):
    cached = search_word_in_cache(word)
    if cached:
        return cached

    return fetch_and_cache_definitions(word)



# ✅ Agregar múltiples definiciones
@user_dictionary_router.post("/add-multiple", response_model=List[UserDictionaryEntry])
def add_selected_definitions(
    user_id: UUID = Query(...),
    definitions: List[UserDictionaryCreate] = Body(...)
):
    if not definitions:
        raise HTTPException(status_code=400, detail="No definitions provided")

    saved = []
    for entry in definitions:
        saved += save_multiple_definitions(user_id, entry.word, [entry])

    return saved

@user_dictionary_router.get("/counts")
def get_word_counts(user_id: UUID = Query(...)):
    active = supabase.table("user_dictionary") \
        .select("count", count="exact") \
        .eq("user_id", str(user_id)) \
        .eq("status", "active") \
        .execute().count
    
    passive = supabase.table("user_dictionary") \
        .select("count", count="exact") \
        .eq("user_id", str(user_id)) \
        .eq("status", "passive") \
        .execute().count
    
    return {"active": active, "passive": passive}

# ✅ Obtener palabras por estado (active/passive)
@user_dictionary_router.get("/by-status", response_model=List[UserDictionaryEntry])
def get_words_by_status_route(
    user_id: UUID = Query(...),
    status: str = Query("active")
):
    return get_words_by_status(user_id, status)


# ✅ Registrar uso de palabra y promover si aplica
@user_dictionary_router.post("/log-usage")
def log_usage_and_check_promotion(
    user_id: UUID = Query(...),
    word_id: UUID = Query(...),
    context: str = Query("chat")
):
    log_word_usage(user_id, word_id, context)
    check_and_promote_word(user_id, word_id)
    return {"success": True, "message": "Usage logged and status checked"}
