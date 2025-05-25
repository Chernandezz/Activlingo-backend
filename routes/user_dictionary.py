from fastapi import APIRouter, HTTPException, Query, Body
from uuid import UUID
from typing import List, Dict
from schemas.user_dictionary import UserDictionaryCreate, UserDictionaryEntry
from services.user_dictionary_service import (
    add_word,
    get_user_dictionary,
    delete_word,
    fetch_definitions_from_api,
    save_multiple_definitions
)

user_dictionary_router = APIRouter()

@user_dictionary_router.post("/", response_model=UserDictionaryEntry)
def save_word(user_id: UUID = Query(...), entry: UserDictionaryCreate = ...):
    return add_word(user_id, entry)


@user_dictionary_router.get("/", response_model=List[UserDictionaryEntry])
def list_words(user_id: UUID = Query(...)):
    return get_user_dictionary(user_id)


@user_dictionary_router.delete("/{word_id}")
def remove_word(word_id: UUID, user_id: UUID = Query(...)):
    success = delete_word(word_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Word not found or already deleted")
    return {"success": True, "message": "Word deleted successfully"}


@user_dictionary_router.get("/search", response_model=List[dict])
def search_definitions(word: str = Query(..., min_length=1)):
    results = fetch_definitions_from_api(word)
    if not results:
        raise HTTPException(status_code=404, detail="No definitions found")
    return results



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
