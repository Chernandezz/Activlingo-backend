# services/user_service.py - VERSIÓN CON MANEJO DE DUPLICADOS
from datetime import datetime, timedelta, timezone
from uuid import UUID
from supabase import create_client, Client
import os
from dotenv import load_dotenv
from typing import Dict, Optional

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_user_profile(user_id: UUID) -> Dict:
    """Obtiene el perfil completo del usuario"""
    try:
        result = (
            supabase.table("users_profile")
            .select("*")
            .eq("id", str(user_id))
            .execute()
        )

        if not result.data or len(result.data) == 0:
            print(f"📝 No profile found for user {user_id}, creating default...")
            return create_default_profile(user_id)

        profile = result.data[0]
        trial_info = process_trial_info(profile)
        
        return {
            "id": profile.get("id"),
            "email": profile.get("email", ""),
            "subscription_type": profile.get("subscription_type", "basic"),
            "is_subscribed": profile.get("is_subscribed", False),
            "trial_active": trial_info["trial_active"],
            "trial_end": trial_info["trial_end"],
            "onboarding_seen": profile.get("onboarding_seen", False),
            "created_at": profile.get("created_at", ""),
        }

    except Exception as e:
        print(f"❌ Error getting user profile: {e}")
        return {
            "error": str(e),
            "id": str(user_id),
            "subscription_type": "basic",
            "is_subscribed": False,
            "trial_active": False,
            "trial_end": None,
            "onboarding_seen": False,
        }

def create_default_profile(user_id: UUID) -> Dict:
    """Crea un perfil por defecto para usuarios nuevos - MANEJA DUPLICADOS"""
    try:
        user_id_str = str(user_id)
        
        # Primero verificar si ya existe el perfil
        existing_check = (
            supabase.table("users_profile")
            .select("*")
            .eq("id", user_id_str)
            .execute()
        )
        
        if existing_check.data and len(existing_check.data) > 0:
            print(f"✅ Profile already exists for user {user_id_str}")
            profile = existing_check.data[0]
            trial_info = process_trial_info(profile)
            return {
                "id": profile.get("id"),
                "email": profile.get("email", ""),
                "subscription_type": profile.get("subscription_type", "basic"),
                "is_subscribed": profile.get("is_subscribed", False),
                "trial_active": trial_info["trial_active"],
                "trial_end": trial_info["trial_end"],
                "onboarding_seen": profile.get("onboarding_seen", False),
                "created_at": profile.get("created_at", ""),
            }
        
        # Si no existe, crear nuevo perfil
        default_profile = {
            "id": user_id_str,
            "subscription_type": "basic",
            "is_subscribed": False,
            "trial_start": datetime.now(timezone.utc).isoformat(),
            "onboarding_seen": False,
        }
        
        print(f"📝 Creating new profile for user {user_id_str}")
        result = supabase.table("users_profile").insert(default_profile).execute()
        
        if result.data:
            trial_end = datetime.now(timezone.utc) + timedelta(days=3)
            return {
                **default_profile,
                "trial_active": True,
                "trial_end": trial_end.isoformat(),
            }
        else:
            raise Exception("Failed to insert profile")
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error creating default profile: {error_msg}")
        
        # Si es error de clave duplicada, intentar obtener el perfil existente
        if "duplicate key" in error_msg.lower() or "23505" in error_msg:
            print(f"🔄 Duplicate key error, fetching existing profile for {user_id_str}")
            try:
                existing = (
                    supabase.table("users_profile")
                    .select("*")
                    .eq("id", user_id_str)
                    .execute()
                )
                
                if existing.data and len(existing.data) > 0:
                    profile = existing.data[0]
                    trial_info = process_trial_info(profile)
                    print(f"✅ Found existing profile for user {user_id_str}")
                    return {
                        "id": profile.get("id"),
                        "email": profile.get("email", ""),
                        "subscription_type": profile.get("subscription_type", "basic"),
                        "is_subscribed": profile.get("is_subscribed", False),
                        "trial_active": trial_info["trial_active"],
                        "trial_end": trial_info["trial_end"],
                        "onboarding_seen": profile.get("onboarding_seen", False),
                        "created_at": profile.get("created_at", ""),
                    }
            except Exception as inner_e:
                print(f"❌ Error fetching existing profile: {inner_e}")
        
        # Si todo falla, devolver perfil básico sin error
        print(f"⚠️ Returning fallback profile for user {user_id_str}")
        return {
            "id": str(user_id),
            "subscription_type": "basic",
            "is_subscribed": False,
            "trial_active": False,
            "trial_end": None,
            "onboarding_seen": False,
        }

def process_trial_info(profile: Dict) -> Dict:
    """Procesa la información del trial del usuario"""
    trial_start_raw = profile.get("trial_start")
    if not trial_start_raw:
        return {"trial_end": None, "trial_active": False}

    try:
        trial_start = datetime.fromisoformat(trial_start_raw.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        trial_end = trial_start + timedelta(days=3)
        expired = now > trial_end

        return {
            "trial_end": trial_end.isoformat(),
            "trial_active": not expired,
        }
    except Exception as e:
        print(f"⚠️ Error processing trial info: {e}")
        return {"trial_end": None, "trial_active": False}

def get_user_plan_type(user_id: UUID) -> str:
    """Obtiene el tipo de plan del usuario - SOLO USAR SUBSCRIPTION_TYPE"""
    try:
        result = (
            supabase.table("users_profile")
            .select("subscription_type, is_subscribed")
            .eq("id", str(user_id))
            .single()
            .execute()
        )
        
        if result.data and result.data.get("subscription_type"):
            return result.data["subscription_type"].lower()
        
        return "basic"
        
    except Exception as e:
        print(f"⚠️ Error getting user plan type: {e}")
        return "basic"

def has_premium_access(user_id: UUID) -> Dict:
    """Verifica si el usuario tiene acceso premium"""
    try:
        profile = get_user_profile(user_id)
        
        # Usuario tiene premium si:
        # 1. Está suscrito Y tiene plan premium
        # 2. O tiene trial activo
        has_premium = (
            (profile.get("is_subscribed", False) and profile.get("subscription_type", "basic") == "premium") or
            profile.get("trial_active", False)
        )
        
        return {
            "has_premium": has_premium,
            "subscription_type": profile.get("subscription_type", "basic"),
            "reason": "subscription" if profile.get("is_subscribed", False) else "trial" if profile.get("trial_active", False) else "none"
        }
        
    except Exception as e:
        print(f"❌ Error checking premium access: {e}")
        return {
            "has_premium": False,
            "subscription_type": "basic",
            "reason": "error"
        }

def get_plan_info(user_id: UUID) -> Dict:
    """Obtiene información detallada del plan del usuario"""
    try:
        premium_access = has_premium_access(user_id)
        
        plan_features = {
            "basic": {
                "name": "Básico",
                "max_suggestions": 3,
                "features": [
                    "IA básica detecta errores principales",
                    "50 correcciones por día",
                    "1 voz para escuchar respuestas",
                    "Tu diccionario personal",
                    "Conversación básica con IA"
                ],
                "analyzer_type": "basic"
            },
            "premium": {
                "name": "Premium", 
                "max_suggestions": 5,
                "features": [
                    "IA súper inteligente - Nuestro mejor modelo",
                    "Correcciones ilimitadas por día",
                    "Voces súper realistas - Como hablar con personas reales",
                    "Te enseña expresiones que usan los nativos",
                    "Adapta tu nivel según cada situación",
                    "Detecta TODO - Gramática, vocabulario y más",
                    "Respuestas instantáneas sin esperar"
                ],
                "analyzer_type": "advanced"
            }
        }
        
        current_plan = "premium" if premium_access["has_premium"] else "basic"
        
        return {
            "current_plan": current_plan,
            "is_premium": premium_access["has_premium"],
            "features": plan_features.get(current_plan, plan_features["basic"])
        }
        
    except Exception as e:
        print(f"❌ Error getting plan info: {e}")
        return {
            "current_plan": "basic",
            "is_premium": False,
            "features": {
                "name": "Básico",
                "max_suggestions": 3,
                "features": ["Acceso básico"],
                "analyzer_type": "basic"
            }
        }

def update_user_plan(user_id: UUID, subscription_type: str) -> Dict:
    """Actualiza el plan del usuario"""
    try:
        if subscription_type not in ["basic", "premium"]:
            return {"success": False, "error": "Invalid subscription type"}
        
        result = (
            supabase.table("users_profile")
            .update({
                "subscription_type": subscription_type,
                "is_subscribed": True,
                "updated_at": datetime.now(timezone.utc).isoformat()
            })
            .eq("id", str(user_id))
            .execute()
        )
        
        if result.data:
            return {
                "success": True,
                "message": f"Plan updated to {subscription_type}",
                "new_plan": subscription_type
            }
        else:
            return {"success": False, "error": "Failed to update plan"}
        
    except Exception as e:
        print(f"❌ Error updating user plan: {e}")
        return {"success": False, "error": str(e)}

def activate_subscription(user_id: str, subscription_type: str = "premium"):
    """Activa la suscripción del usuario"""
    try:
        supabase.table("users_profile").update({
            "is_subscribed": True,
            "subscription_type": subscription_type,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", user_id).execute()
        
        return {"success": True, "plan": subscription_type}
    except Exception as e:
        print(f"❌ Error activating subscription: {e}")
        return {"success": False, "error": str(e)}

def mark_onboarding_seen(user_id: str):
    """Marca el onboarding como visto"""
    try:
        supabase.table("users_profile").update({
            "onboarding_seen": True,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", user_id).execute()
        
        return {"success": True}
    except Exception as e:
        print(f"❌ Error marking onboarding seen: {e}")
        return {"success": False, "error": str(e)}

# Funciones legacy para compatibilidad
def is_trial_active(user_id: UUID) -> Dict:
    """Función legacy - mantener para compatibilidad"""
    profile = get_user_profile(user_id)
    return {
        "trial_end": profile.get("trial_end"),
        "trial_active": profile.get("trial_active", False),
        "is_subscribed": profile.get("is_subscribed", False),
        "onboarding_seen": profile.get("onboarding_seen", False),
    }