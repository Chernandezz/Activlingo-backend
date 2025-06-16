# user_dictionary_router.py - ROUTES OPTIMIZADAS SIN REDIS

from fastapi import APIRouter, HTTPException, Query, Body, Depends
from uuid import UUID
from typing import List, Dict

from services.user_dictionary_service import (
    add_word,
    fetch_definitions,
    get_user_dictionary_cached,
    delete_word,
    get_words_by_status,
    log_word_usage,
    check_and_promote_word,
    suggest_similar_words,
    invalidate_user_cache,
    get_cache_stats,
    clear_all_caches
)
from schemas.user_dictionary import UserDictionaryCreate, UserDictionaryEntry
from dependencies.auth import get_current_user

user_dictionary_router = APIRouter()


@user_dictionary_router.post("/", response_model=UserDictionaryEntry)
async def save_word(
    entry: UserDictionaryCreate = Body(...),
    user_id: UUID = Depends(get_current_user)
):
    try:
        result = await add_word(user_id, entry)
        # El cache se invalida automáticamente en add_word
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@user_dictionary_router.get("/", response_model=List[UserDictionaryEntry])
def list_words(
    skip: int = 0,
    limit: int = 50,
    user_id: UUID = Depends(get_current_user)
):
    # Usar versión con cache en memoria
    all_words = get_user_dictionary_cached(str(user_id))
    return all_words[skip: skip + limit]


@user_dictionary_router.delete("/{word_id}")
def remove_word(
    word_id: UUID,
    user_id: UUID = Depends(get_current_user)
):
    if not delete_word(word_id, user_id):
        raise HTTPException(status_code=404, detail="Word not found")
    
    # El cache se invalida automáticamente en delete_word
    return {"success": True}


@user_dictionary_router.get("/search", response_model=List[Dict])
async def search_definitions(word: str = Query(..., min_length=1)):
    try:
        # Usa tu cache de Supabase existente (¡perfecto!)
        return await fetch_definitions(word)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Search error: {e}")


# NUEVO ENDPOINT OPTIMIZADO - Combina búsqueda + verificación de usuario
@user_dictionary_router.get("/search-with-user-check", response_model=List[Dict])
async def search_with_user_check(
    word: str = Query(..., min_length=1),
    user_id: UUID = Depends(get_current_user)
):
    """
    Endpoint optimizado que devuelve definiciones con flags de si ya están agregadas.
    Reduce las consultas del frontend de 2 a 1.
    """
    try:
        # Buscar definiciones (usa tu cache de Supabase)
        definitions = await fetch_definitions(word)
        if not definitions:
            return []
        
        # Obtener palabras del usuario (con cache en memoria)
        user_words = get_user_dictionary_cached(str(user_id))
        
        # Marcar cuáles ya están agregadas
        results_with_flags = []
        for definition in definitions:
            already_exists = any(
                w.word.lower() == word.lower() and 
                w.meaning.strip().lower() == definition["meaning"].strip().lower()
                for w in user_words
            )
            results_with_flags.append({
                **definition,
                "added": already_exists
            })
        
        return results_with_flags
        
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Search error: {e}")


@user_dictionary_router.get("/by-status", response_model=List[UserDictionaryEntry])
def get_by_status(
    status: str = Query("active"),
    user_id: UUID = Depends(get_current_user)
):
    # Usa cache automáticamente
    return get_words_by_status(user_id, status)


@user_dictionary_router.post("/log-usage")
def log_usage_and_check_promotion(
    word_id: UUID = Query(...),
    context: str = Query("general"),
    user_id: UUID = Depends(get_current_user)
):
    log_word_usage(user_id, word_id, context)
    check_and_promote_word(user_id, word_id)
    
    # El cache se invalida automáticamente en log_word_usage
    return {"success": True}


@user_dictionary_router.get("/suggestions", response_model=List[Dict])
def get_word_suggestions(
    prefix: str = Query(..., min_length=1),
    limit: int = 20
):
    try:
        return suggest_similar_words(prefix, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ENDPOINTS PARA GESTIÓN DE CACHE (útil para desarrollo/debugging)
@user_dictionary_router.post("/clear-cache")
def clear_user_cache(
    user_id: UUID = Depends(get_current_user)
):
    invalidate_user_cache(str(user_id))
    return {"success": True, "message": f"Cache cleared for user {user_id}"}


@user_dictionary_router.get("/cache-stats")
def cache_statistics():
    """Endpoint para ver estadísticas del cache"""
    return get_cache_stats()


@user_dictionary_router.post("/clear-all-cache")
def clear_all_cache():
    """SOLO PARA DESARROLLO - Limpiar todo el cache"""
    clear_all_caches()
    return {"success": True, "message": "All caches cleared"}