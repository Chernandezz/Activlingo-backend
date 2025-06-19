# routes/user.py - LIMPIO Y ORGANIZADO
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

from schemas.user_schemas import UpdateProfileRequest
from services.user_service import (
    get_full_user_profile,
    update_user_profile,
    get_user_achievements,
    mark_onboarding_seen
)
from dependencies.auth import get_current_user

user_router = APIRouter()

@user_router.get("/profile")
def get_profile(user_id: UUID = Depends(get_current_user)):
    """Obtiene el perfil completo del usuario"""
    try:
        return get_full_user_profile(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@user_router.put("/profile")
def update_profile(
    updates: UpdateProfileRequest,
    user_id: UUID = Depends(get_current_user)
):
    """Actualiza el perfil del usuario"""
    try:
        update_data = {k: v for k, v in updates.dict().items() if v is not None}
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No data provided")
        
        return update_user_profile(user_id, update_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@user_router.get("/stats")
def get_stats(user_id: UUID = Depends(get_current_user)):
    """Obtiene estadísticas del usuario"""
    try:
        profile = get_full_user_profile(user_id)
        return profile.get("stats", {})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@user_router.get("/achievements")
def get_achievements(user_id: UUID = Depends(get_current_user)):
    """Obtiene logros del usuario"""
    try:
        return get_user_achievements(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@user_router.post("/onboarding-seen")
def mark_onboarding_complete(user_id: UUID = Depends(get_current_user)):
    """Marca el onboarding como completado"""
    try:
        return mark_onboarding_seen(str(user_id))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))