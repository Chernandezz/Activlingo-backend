# routes/subscription.py - LIMPIO Y ORGANIZADO
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

from schemas.subscription_schemas import CheckoutRequest, TrialRequest
from services.subscription_service import (
    create_checkout_session,
    cancel_subscription,
    get_user_subscription_status,
    get_available_plans
)
from services.user_service import start_user_trial
from dependencies.auth import get_current_user

subscription_router = APIRouter()

# ========== ENDPOINTS PRINCIPALES ==========

@subscription_router.get("/plans")
def get_plans():
    """Obtiene todos los planes disponibles"""
    try:
        return get_available_plans()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@subscription_router.get("/status")
def get_status(user_id: UUID = Depends(get_current_user)):
    """Obtiene el estado completo de suscripción del usuario"""
    try:
        return get_user_subscription_status(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@subscription_router.post("/checkout")
def create_checkout(
    request: CheckoutRequest,
    user_id: UUID = Depends(get_current_user)
):
    """Crea una sesión de pago de Stripe"""
    try:
        result = create_checkout_session(
            user_id=user_id,
            plan_slug=request.plan_slug,
            billing_interval=request.billing_interval
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return {
            "checkout_url": result.get("checkout_url"),
            "session_id": result.get("session_id")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@subscription_router.post("/trial/start")
def start_trial(
    request: TrialRequest,
    user_id: UUID = Depends(get_current_user)
):
    """Inicia el período de prueba gratuita"""
    try:
        if not request.accept_terms:
            raise HTTPException(status_code=400, detail="Must accept terms")
            
        result = start_user_trial(user_id)
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message"))
        
        return {
            "trial_start": result.get("trial_start"),
            "trial_end": result.get("trial_end"),
            "message": result.get("message")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@subscription_router.post("/cancel")
def cancel_current_subscription(user_id: UUID = Depends(get_current_user)):
    """Cancela la suscripción actual"""
    try:
        result = cancel_subscription(user_id)
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return {
            "message": result.get("message"),
            "ends_at": result.get("ends_at")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))