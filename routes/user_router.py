# routes/user.py - ROUTES ACTUALIZADAS
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from services.user_service import (
    is_trial_active, 
    mark_onboarding_seen,
    get_user_profile,
    get_user_plan_type,
    has_premium_access,
    get_plan_info,
    update_user_plan
)
from dependencies.auth import get_current_user
from uuid import UUID

user_router = APIRouter()

# 🆕 Modelo para actualizar plan
class UpdatePlanRequest(BaseModel):
    subscription_type: str  # 'basic' | 'premium'

# Endpoints existentes
@user_router.get("/trial-status")
def check_trial_status(user_id: UUID = Depends(get_current_user)):
    """Obtiene el estado del trial del usuario"""
    return is_trial_active(user_id)

@user_router.post("/onboarding-seen")
def mark_seen(user_id: UUID = Depends(get_current_user)):
    """Marca el onboarding como visto"""
    return mark_onboarding_seen(str(user_id))

# 🆕 Nuevos endpoints
@user_router.get("/profile")
def get_user_profile_endpoint(user_id: UUID = Depends(get_current_user)):
    """Obtiene el perfil completo del usuario"""
    try:
        profile = get_user_profile(user_id)
        return profile
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting user profile: {str(e)}")

@user_router.get("/plan-info")
def get_user_plan_info(user_id: UUID = Depends(get_current_user)):
    """Obtiene información detallada del plan del usuario"""
    try:
        plan_info = get_plan_info(user_id)
        return plan_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting plan info: {str(e)}")

@user_router.get("/premium-access")
def check_premium_access(user_id: UUID = Depends(get_current_user)):
    """Verifica si el usuario tiene acceso premium"""
    try:
        access_info = has_premium_access(user_id)
        return access_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking premium access: {str(e)}")

@user_router.post("/update-plan")
def update_plan(
    request: UpdatePlanRequest,
    user_id: UUID = Depends(get_current_user)
):
    """Actualiza el plan del usuario (para cuando se suscriban)"""
    try:
        result = update_user_plan(user_id, request.subscription_type)
        
        if result.get("success"):
            return result
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to update plan"))
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating plan: {str(e)}")

@user_router.get("/plan-type")
def get_plan_type(user_id: UUID = Depends(get_current_user)):
    """Obtiene solo el tipo de plan del usuario (para análisis)"""
    try:
        plan_type = get_user_plan_type(user_id)
        return {"plan_type": plan_type}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting plan type: {str(e)}")

# 🆕 Endpoint de debug
@user_router.get("/debug")
def debug_user_info(user_id: UUID = Depends(get_current_user)):
    """Debug endpoint para verificar información del usuario"""
    try:
        profile = get_user_profile(user_id)
        plan_info = get_plan_info(user_id)
        premium_access = has_premium_access(user_id)
        
        return {
            "user_id": str(user_id),
            "profile": profile,
            "plan_info": plan_info,
            "premium_access": premium_access,
            "debug_timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "error": str(e),
            "user_id": str(user_id)
        }