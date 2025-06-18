# routes/subscription.py - CORREGIDO CON ENDPOINTS FALTANTES
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from services.subscription_service import (
    create_checkout_session,
    cancel_subscription,
    get_user_plan_access
)
from services.user_service import (
    get_available_plans, 
    get_current_subscription,
    start_user_trial
)
from services.webhook_service import get_subscription_events
from dependencies.auth import get_current_user

subscription_router = APIRouter()

# ========== MODELOS ==========

class CreateCheckoutRequest(BaseModel):
    plan_slug: str
    billing_interval: str = "monthly"

class TrialRequest(BaseModel):
    accept_terms: bool = True

# ========== ENDPOINTS DE PLANES ==========

@subscription_router.get("/plans")
def get_subscription_plans():
    """Obtiene todos los planes de suscripción disponibles"""
    try:
        plans = get_available_plans()
        return {"success": True, "plans": plans}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting plans: {str(e)}")

# ========== ENDPOINTS DE SUSCRIPCIÓN ACTUAL ==========

@subscription_router.get("/current")
def get_current_subscription_endpoint(user_id: UUID = Depends(get_current_user)):
    """Obtiene la suscripción actual del usuario"""
    try:
        subscription = get_current_subscription(user_id)
        if subscription:
            return {"success": True, "subscription": subscription}
        else:
            return {"success": True, "subscription": None, "message": "No active subscription"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting subscription: {str(e)}")

@subscription_router.get("/access")
def get_plan_access(user_id: UUID = Depends(get_current_user)):
    """Obtiene información de acceso basada en el plan del usuario"""
    try:
        access_info = get_user_plan_access(user_id)
        return {"success": True, "access": access_info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting access info: {str(e)}")

# ========== ENDPOINTS DE TRIAL ==========

@subscription_router.post("/trial/start")
def start_trial_endpoint(
    request: TrialRequest,
    user_id: UUID = Depends(get_current_user)
):
    """Activa el periodo de prueba gratuita"""
    try:
        if not request.accept_terms:
            raise HTTPException(status_code=400, detail="Must accept terms to start trial")
            
        result = start_user_trial(user_id)
        
        if result.get("success"):
            return result
        else:
            raise HTTPException(status_code=400, detail=result.get("message", "Failed to start trial"))
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting trial: {str(e)}")

# ========== ENDPOINTS DE CHECKOUT ==========

@subscription_router.post("/checkout")
def create_checkout_endpoint(
    request: CreateCheckoutRequest,
    user_id: UUID = Depends(get_current_user)
):
    """Crea una sesión de checkout de Stripe"""
    try:
        result = create_checkout_session(
            user_id=user_id,
            plan_slug=request.plan_slug,
            billing_interval=request.billing_interval
        )
        
        if result.get("success"):
            return {
                "success": True,
                "checkout_url": result.get("checkout_url"),
                "session_id": result.get("session_id")
            }
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to create checkout"))
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating checkout: {str(e)}")

# ========== NUEVO: ENDPOINT UPGRADE (para compatibilidad con Angular) ==========

@subscription_router.post("/upgrade")
def create_upgrade_endpoint(
    request: CreateCheckoutRequest,
    user_id: UUID = Depends(get_current_user)
):
    """
    Crea una sesión de upgrade/checkout de Stripe (alias para compatibilidad)
    Este endpoint es el que Angular está llamando
    """
    try:
        print(f"🔄 Usuario {user_id} solicitando upgrade a plan: {request.plan_slug}")
        
        result = create_checkout_session(
            user_id=user_id,
            plan_slug=request.plan_slug,
            billing_interval=request.billing_interval
        )
        
        if result.get("success"):
            print(f"✅ Checkout URL creada: {result.get('checkout_url')}")
            return {
                "success": True,
                "checkout_url": result.get("checkout_url"),
                "session_id": result.get("session_id")
            }
        else:
            print(f"❌ Error creando checkout: {result.get('error')}")
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to create checkout"))
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error crítico en upgrade: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating checkout: {str(e)}")

# ========== ENDPOINTS DE GESTIÓN ==========

@subscription_router.post("/cancel")
def cancel_subscription_endpoint(user_id: UUID = Depends(get_current_user)):
    """Cancela la suscripción actual del usuario"""
    try:
        result = cancel_subscription(user_id)
        
        if result.get("success"):
            return result
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to cancel subscription"))
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error canceling subscription: {str(e)}")

@subscription_router.post("/reactivate")
def reactivate_subscription_endpoint(user_id: UUID = Depends(get_current_user)):
    """Reactiva una suscripción cancelada (antes del fin del periodo)"""
    try:
        # Obtener suscripción actual
        subscription = get_current_subscription(user_id)
        
        if not subscription:
            raise HTTPException(status_code=404, detail="No subscription found")
            
        if subscription.get("status") != "canceled":
            raise HTTPException(status_code=400, detail="Subscription is not canceled")
            
        # Reactivar en Stripe
        import stripe
        stripe_subscription_id = subscription.get("stripe_subscription_id")
        
        if stripe_subscription_id:
            stripe.Subscription.modify(
                stripe_subscription_id,
                cancel_at_period_end=False
            )
            
            # Actualizar en BD
            from services.subscription_service import supabase
            supabase.table("user_subscriptions").update({
                "status": "active",
                "canceled_at": None,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("stripe_subscription_id", stripe_subscription_id).execute()
            
            return {"success": True, "message": "Subscription reactivated successfully"}
        else:
            raise HTTPException(status_code=400, detail="Cannot reactivate subscription")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reactivating subscription: {str(e)}")

# ========== ENDPOINTS DE HISTORIAL ==========

@subscription_router.get("/history")
def get_subscription_history(user_id: UUID = Depends(get_current_user)):
    """Obtiene el historial de eventos de suscripción del usuario"""
    try:
        events = get_subscription_events(str(user_id))
        return events
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting history: {str(e)}")

# ========== ENDPOINTS DE INFORMACIÓN ==========

@subscription_router.get("/status")
def get_subscription_status(user_id: UUID = Depends(get_current_user)):
    """Obtiene un resumen completo del estado de suscripción"""
    try:
        subscription = get_current_subscription(user_id)
        access_info = get_user_plan_access(user_id)
        
        # Determinar estado general
        if not subscription:
            status = "no_subscription"
            message = "No tienes una suscripción activa"
        elif subscription.get("status") == "trial":
            status = "trial"
            message = "Estás en periodo de prueba"
        elif subscription.get("status") == "active":
            status = "active"
            message = "Suscripción activa"
        elif subscription.get("status") == "canceled":
            status = "canceled"
            message = "Suscripción cancelada"
        else:
            status = "unknown"
            message = "Estado desconocido"
        
        return {
            "success": True,
            "status": status,
            "message": message,
            "subscription": subscription,
            "access": access_info,
            "can_upgrade": status in ["no_subscription", "trial"],
            "can_cancel": status == "active",
            "can_reactivate": status == "canceled"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting status: {str(e)}")

# ========== ENDPOINTS LEGACY (compatibilidad) ==========

@subscription_router.get("/premium-access")
def check_premium_access_legacy(user_id: UUID = Depends(get_current_user)):
    """Verifica si el usuario tiene acceso premium - LEGACY"""
    try:
        access_info = get_user_plan_access(user_id)
        return {
            "success": True,
            "has_premium": access_info.get("has_premium", False),
            "plan_type": access_info.get("plan_slug", "basic")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking premium access: {str(e)}")

# ========== ENDPOINTS DE DEBUG ==========

@subscription_router.get("/debug/user/{user_id}")
def debug_user_subscription(user_id: UUID = Depends(get_current_user)):
    """Endpoint de debug para verificar estado del usuario"""
    try:
        from services.subscription_service import supabase
        
        # Verificar usuario en auth
        auth_user = supabase.auth.admin.get_user_by_id(str(user_id))
        
        # Verificar suscripciones
        subscriptions = supabase.table("user_subscriptions").select("*").eq("user_id", str(user_id)).execute()
        
        # Verificar planes disponibles
        plans = supabase.table("subscription_plans").select("*").eq("is_active", True).execute()
        
        return {
            "success": True,
            "debug_info": {
                "user_exists": auth_user.user is not None,
                "user_email": auth_user.user.email if auth_user.user else None,
                "user_id": str(user_id),
                "subscriptions": subscriptions.data,
                "available_plans": plans.data,
                "current_subscription": get_current_subscription(user_id)
            }
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}