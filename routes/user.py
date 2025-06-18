# routes/user.py - LIMPIO (SIN DUPLICADOS)
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

from services.user_service import (
    is_trial_active, 
    mark_onboarding_seen,
    get_full_user_profile,
    get_user_achievements,
    update_user_profile
)
from dependencies.auth import get_current_user

user_router = APIRouter()

# ========== MODELOS ==========

class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    language: Optional[str] = None
    learning_goal: Optional[str] = None
    difficulty_level: Optional[str] = None
    notifications: Optional[dict] = None

# ========== ENDPOINTS DE PERFIL ==========

@user_router.get("/profile")
def get_user_profile_endpoint(user_id: UUID = Depends(get_current_user)):
    """Obtiene el perfil completo del usuario con estadísticas y suscripción"""
    try:
        profile = get_full_user_profile(user_id)
        return {"success": True, "profile": profile}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting user profile: {str(e)}")

@user_router.put("/profile")
def update_user_profile_endpoint(
    updates: UpdateProfileRequest,
    user_id: UUID = Depends(get_current_user)
):
    """Actualiza el perfil del usuario"""
    try:
        # Convertir a diccionario excluyendo None
        update_data = {k: v for k, v in updates.dict().items() if v is not None}
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No data provided to update")
        
        result = update_user_profile(user_id, update_data)
        
        if result.get("success"):
            return result
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to update profile"))
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating profile: {str(e)}")

# ========== ENDPOINTS DE ESTADÍSTICAS ==========

@user_router.get("/stats")
def get_user_stats_endpoint(user_id: UUID = Depends(get_current_user)):
    """Obtiene las estadísticas del usuario"""
    try:
        profile = get_full_user_profile(user_id)
        stats = profile.get("stats", {})
        return {"success": True, "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting user stats: {str(e)}")

# ========== ENDPOINTS DE LOGROS ==========

@user_router.get("/achievements")
def get_user_achievements_endpoint(user_id: UUID = Depends(get_current_user)):
    """Obtiene todos los logros del usuario"""
    try:
        achievements = get_user_achievements(user_id)
        return {"success": True, "achievements": achievements}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting achievements: {str(e)}")

# ========== ENDPOINTS DE ONBOARDING ==========

@user_router.post("/onboarding-seen")
def mark_onboarding_seen_endpoint(user_id: UUID = Depends(get_current_user)):
    """Marca el onboarding como visto"""
    try:
        result = mark_onboarding_seen(str(user_id))
        if result.get("success"):
            return {"success": True, "message": "Onboarding marked as seen"}
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to mark onboarding"))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error marking onboarding: {str(e)}")

# ========== ENDPOINTS LEGACY (mantener compatibilidad) ==========

@user_router.get("/trial-status")
def check_trial_status_legacy(user_id: UUID = Depends(get_current_user)):
    """Obtiene el estado del trial del usuario - LEGACY"""
    try:
        status = is_trial_active(user_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking trial status: {str(e)}")

@user_router.get("/plan-info")
def get_user_plan_info_legacy(user_id: UUID = Depends(get_current_user)):
    """Obtiene información del plan del usuario - LEGACY"""
    try:
        from services.subscription_service import get_user_plan_access
        access_info = get_user_plan_access(user_id)
        
        return {
            "success": True,
            "plan_info": {
                "current_plan": access_info.get("plan_slug", "basic"),
                "is_premium": access_info.get("has_premium", False),
                "features": {
                    "name": "Premium" if access_info.get("has_premium") else "Básico",
                    "max_suggestions": 5 if access_info.get("has_premium") else 3,
                    "features": [
                        "Conversaciones ilimitadas" if access_info.get("has_premium") else "5 conversaciones por día",
                        "IA avanzada" if access_info.get("has_premium") else "IA básica",
                        "Soporte prioritario" if access_info.get("priority_support") else "Soporte estándar"
                    ],
                    "analyzer_type": "advanced" if access_info.get("has_premium") else "basic"
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting plan info: {str(e)}")

@user_router.get("/premium-access")
def check_premium_access_legacy(user_id: UUID = Depends(get_current_user)):
    """Verifica si el usuario tiene acceso premium - LEGACY"""
    try:
        from services.subscription_service import get_user_plan_access
        access_info = get_user_plan_access(user_id)
        return {
            "success": True,
            "access": {
                "has_premium": access_info.get("has_premium", False),
                "plan_type": access_info.get("plan_slug", "basic")
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking premium access: {str(e)}")

# ========== ENDPOINT DE DEBUG ==========

@user_router.get("/debug")
def debug_user_info(user_id: UUID = Depends(get_current_user)):
    """Debug endpoint para verificar información del usuario"""
    try:
        profile = get_full_user_profile(user_id)
        achievements = get_user_achievements(user_id)
        
        from services.subscription_service import get_user_plan_access
        access_info = get_user_plan_access(user_id)
        
        return {
            "success": True,
            "debug_info": {
                "user_id": str(user_id),
                "profile": profile,
                "achievements": achievements,
                "access_info": access_info,
                "debug_timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "user_id": str(user_id)
        }