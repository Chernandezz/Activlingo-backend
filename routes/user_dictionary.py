from fastapi import APIRouter, HTTPException, Query
from typing import List
from uuid import UUID
from schemas.user_dictionary import UserDictionaryCreate, UserDictionaryEntry
from services.user_dictionary_service import add_word, get_user_dictionary, delete_word

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
    return {"success": True, "message": "Word deleted"}
