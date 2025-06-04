# routers/user_dictionary_router.py

from fastapi import APIRouter, HTTPException, Query, Body
from uuid import UUID
from typing import List, Dict

from services.user_dictionary_service import (
    add_word,
    fetch_definitions,
    get_user_dictionary,
    delete_word,
    get_words_by_status,
    log_word_usage,
    check_and_promote_word,
    suggest_similar_words
)
from schemas.user_dictionary import UserDictionaryCreate, UserDictionaryEntry

user_dictionary_router = APIRouter()

@user_dictionary_router.post("/", response_model=UserDictionaryEntry)
async def save_word(user_id: UUID = Query(...), entry: UserDictionaryCreate = Body(...)):
    try:
        return await add_word(user_id, entry)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@user_dictionary_router.get("/", response_model=List[UserDictionaryEntry])
def list_words(user_id: UUID = Query(...), skip: int = 0, limit: int = 50):
    all_words = get_user_dictionary(user_id)
    return all_words[skip: skip + limit]

@user_dictionary_router.delete("/{word_id}")
def remove_word(word_id: UUID, user_id: UUID = Query(...)):
    if not delete_word(word_id, user_id):
        raise HTTPException(status_code=404, detail="Word not found")
    return {"success": True}

@user_dictionary_router.get("/search", response_model=List[Dict])
async def search_definitions(word: str = Query(..., min_length=1)):
    try:
        return await fetch_definitions(word)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"WordsAPI error: {e}")


@user_dictionary_router.get("/by-status", response_model=List[UserDictionaryEntry])
def get_by_status(user_id: UUID = Query(...), status: str = Query("active")):
    return get_words_by_status(user_id, status)

@user_dictionary_router.post("/log-usage")
def log_usage_and_check_promotion(
    user_id: UUID = Query(...),
    word_id: UUID = Query(...),
    context: str = Query("general")
):
    log_word_usage(user_id, word_id, context)
    check_and_promote_word(user_id, word_id)
    return {"success": True}

@user_dictionary_router.get("/suggestions", response_model=List[Dict])
def get_word_suggestions(prefix: str = Query(..., min_length=1), limit: int = 20):
    try:
        return suggest_similar_words(prefix, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))