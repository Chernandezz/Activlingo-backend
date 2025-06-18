# services/user_service.py - LIMPIO Y ORGANIZADO
from datetime import datetime, timedelta, timezone
from uuid import UUID
from supabase import create_client, Client
import os
from dotenv import load_dotenv
from typing import Dict, Optional, List

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ========== PERFIL COMPLETO ==========

def get_full_user_profile(user_id: UUID) -> Dict:
    """Obtiene el perfil completo del usuario con estadísticas y suscripción"""
    try:
        user_id_str = str(user_id)
        
        # Obtener usuario de auth
        auth_user = supabase.auth.admin.get_user_by_id(user_id_str)
        
        # Obtener o crear perfil básico
        profile = get_or_create_profile(user_id)
        
        # Obtener estadísticas
        stats = get_user_stats(user_id)
        
        # Obtener suscripción actual
        subscription = get_current_subscription(user_id)
        
        return {
            "user": {
                "id": user_id_str,
                "email": auth_user.user.email if auth_user and auth_user.user else "",
                "name": auth_user.user.user_metadata.get("full_name", "") if auth_user and auth_user.user else "",
                "avatar_url": auth_user.user.user_metadata.get("avatar_url", "") if auth_user and auth_user.user else "",
                "created_at": str(auth_user.user.created_at) if auth_user and auth_user.user else "",
            },
            "stats": stats,
            "subscription": subscription,
            "profile": profile
        }
        
    except Exception as e:
        print(f"❌ Error getting full user profile: {e}")
        return {
            "user": {"id": str(user_id), "email": "", "name": "", "avatar_url": "", "created_at": ""},
            "stats": get_default_stats(),
            "subscription": None,
            "profile": {"onboarding_seen": False}
        }

def get_or_create_profile(user_id: UUID) -> Dict:
    """Obtiene o crea el perfil básico del usuario"""
    try:
        user_id_str = str(user_id)
        
        result = supabase.table("users_profile").select("*").eq("id", user_id_str).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        
        # Crear perfil básico
        now = datetime.now(timezone.utc).isoformat()
        new_profile = {
            "id": user_id_str,
            "trial_start": now,
            "onboarding_seen": False,
            "created_at": now,
            "updated_at": now
        }
        
        result = supabase.table("users_profile").insert(new_profile).execute()
        create_initial_user_stats(user_id)
        
        return result.data[0] if result.data else new_profile
        
    except Exception as e:
        print(f"❌ Error getting/creating profile: {e}")
        return {"id": str(user_id), "onboarding_seen": False}

def update_user_profile(user_id: UUID, updates: Dict) -> Dict:
    """Actualiza el perfil del usuario"""
    try:
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        result = supabase.table("users_profile").update(updates).eq("id", str(user_id)).execute()
        
        return {"message": "Profile updated successfully"}
        
    except Exception as e:
        print(f"❌ Error updating profile: {e}")
        raise Exception(f"Failed to update profile: {str(e)}")

# ========== ESTADÍSTICAS ==========

def get_user_stats(user_id: UUID) -> Dict:
    """Obtiene las estadísticas del usuario"""
    try:
        result = supabase.table("user_stats").select("*").eq("user_id", str(user_id)).execute()
        
        if result.data and len(result.data) > 0:
            stats = result.data[0]
            return {
                "total_conversations": stats.get("total_conversations", 0),
                "current_streak": stats.get("current_streak", 0),
                "longest_streak": stats.get("longest_streak", 0),
                "total_words_learned": stats.get("total_words_learned", 0),
                "average_session_minutes": calculate_average_session(stats),
                "join_date": stats.get("created_at", ""),
                "last_activity": stats.get("last_activity_at", ""),
                "conversations_this_month": stats.get("conversations_this_month", 0),
                "words_learned_this_month": stats.get("words_this_month", 0)
            }
        else:
            return create_initial_user_stats(user_id)
            
    except Exception as e:
        print(f"❌ Error getting user stats: {e}")
        return get_default_stats()

def create_initial_user_stats(user_id: UUID) -> Dict:
    """Crea estadísticas iniciales para el usuario"""
    try:
        initial_stats = {
            "user_id": str(user_id),
            "total_conversations": 0,
            "current_streak": 0,
            "longest_streak": 0,
            "total_words_learned": 0,
            "total_session_minutes": 0,
            "conversations_this_month": 0,
            "words_this_month": 0,
            "last_activity_at": datetime.now(timezone.utc).isoformat(),
            "streak_updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        result = supabase.table("user_stats").insert(initial_stats).execute()
        
        if result.data:
            stats = result.data[0]
            return {
                "total_conversations": 0,
                "current_streak": 0,
                "longest_streak": 0,
                "total_words_learned": 0,
                "average_session_minutes": 0,
                "join_date": stats.get("created_at", ""),
                "last_activity": stats.get("last_activity_at", ""),
                "conversations_this_month": 0,
                "words_learned_this_month": 0
            }
        
        return get_default_stats()
        
    except Exception as e:
        print(f"❌ Error creating initial stats: {e}")
        return get_default_stats()

def get_default_stats() -> Dict:
    """Retorna estadísticas por defecto"""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "total_conversations": 0,
        "current_streak": 0,
        "longest_streak": 0,
        "total_words_learned": 0,
        "average_session_minutes": 0,
        "join_date": now,
        "last_activity": now,
        "conversations_this_month": 0,
        "words_learned_this_month": 0
    }

def calculate_average_session(stats: Dict) -> int:
    """Calcula el promedio de minutos por sesión"""
    total_minutes = stats.get("total_session_minutes", 0)
    total_conversations = stats.get("total_conversations", 0)
    
    return int(total_minutes / total_conversations) if total_conversations > 0 else 0

# ========== SUSCRIPCIONES ==========

def get_current_subscription(user_id: UUID) -> Optional[Dict]:
    """Obtiene la suscripción actual del usuario"""
    try:
        # Buscar suscripción activa
        result = (
            supabase.table("user_subscriptions")
            .select("""
                *,
                subscription_plans(*)
            """)
            .eq("user_id", str(user_id))
            .eq("status", "active")
            .limit(1)
            .execute()
        )

        if result.data and len(result.data) > 0:
            sub = result.data[0]
            plan = sub.get("subscription_plans", {})

            return {
                "id": sub.get("id"),
                "status": sub.get("status"),
                "plan": {
                    "id": plan.get("id"),
                    "name": plan.get("name"),
                    "slug": plan.get("slug"),
                    "price": plan.get("price"),
                    "currency": plan.get("currency"),
                    "billing_interval": plan.get("billing_interval"),
                },
                "starts_at": sub.get("starts_at"),
                "ends_at": sub.get("ends_at"),
                "current_period_end": sub.get("current_period_end")
            }

        # Si no hay suscripción activa, verificar trial
        return check_trial_subscription(user_id)

    except Exception as e:
        print(f"❌ Error getting current subscription: {e}")
        return check_trial_subscription(user_id)

def check_trial_subscription(user_id: UUID) -> Optional[Dict]:
    """Verifica si el usuario tiene trial activo"""
    try:
        result = (
            supabase.table("users_profile")
            .select("trial_start")
            .eq("id", str(user_id))
            .execute()
        )
        
        if result.data and len(result.data) > 0 and result.data[0].get("trial_start"):
            trial_start = datetime.fromisoformat(
                result.data[0]["trial_start"].replace("Z", "+00:00")
            )
            trial_end = trial_start + timedelta(days=3)
            now = datetime.now(timezone.utc)
            
            if now <= trial_end:
                return {
                    "id": None,
                    "status": "trial",
                    "plan": {
                        "id": None,
                        "name": "Prueba Gratuita",
                        "slug": "trial",
                        "price": 0,
                        "currency": "USD",
                        "billing_interval": "trial",
                    },
                    "starts_at": trial_start.isoformat(),
                    "ends_at": trial_end.isoformat(),
                    "current_period_end": trial_end.isoformat()
                }
        
        return None
        
    except Exception as e:
        print(f"❌ Error checking trial: {e}")
        return None

def get_available_plans() -> List[Dict]:
    """Obtiene todos los planes disponibles"""
    try:
        result = (
            supabase.table("subscription_plans")
            .select("*")
            .eq("is_active", True)
            .order("sort_order")
            .execute()
        )
        
        plans = []
        for plan in result.data:
            plans.append({
                "id": plan.get("id"),
                "name": plan.get("name"),
                "slug": plan.get("slug"),
                "price": plan.get("price"),
                "currency": plan.get("currency"),
                "billing_interval": plan.get("billing_interval"),
                "features": plan.get("features", []),
                "stripe_price_id": plan.get("stripe_price_id")
            })
        
        return plans
        
    except Exception as e:
        print(f"❌ Error getting available plans: {e}")
        return []

# ========== TRIAL ==========

def start_user_trial(user_id: UUID) -> Dict:
    """Inicia el período de prueba gratuita"""
    try:
        now = datetime.now(timezone.utc)
        trial_end = now + timedelta(days=3)

        supabase.table("users_profile").update({
            "trial_start": now.isoformat(),
            "onboarding_seen": True,
            "updated_at": now.isoformat()
        }).eq("id", str(user_id)).execute()

        return {
            "success": True,
            "message": "Trial started successfully",
            "trial_start": now.isoformat(),
            "trial_end": trial_end.isoformat()
        }

    except Exception as e:
        print(f"❌ Error starting trial: {e}")
        return {"success": False, "message": "Failed to start trial"}

# ========== LOGROS ==========

def get_user_achievements(user_id: UUID) -> Dict:
    """Obtiene los logros del usuario"""
    try:
        # Logros de ejemplo - implementar lógica real después
        achievements = [
            {
                "id": "1",
                "title": "Primera conversación",
                "description": "Completa tu primera conversación",
                "icon": "fas fa-comment",
                "unlocked": True,
                "unlocked_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "id": "2", 
                "title": "Racha de 7 días",
                "description": "Mantén una racha de 7 días",
                "icon": "fas fa-fire",
                "unlocked": False,
                "unlocked_at": None
            }
        ]
        
        total_unlocked = sum(1 for a in achievements if a["unlocked"])
        
        return {
            "achievements": achievements,
            "total_unlocked": total_unlocked
        }
        
    except Exception as e:
        print(f"❌ Error getting achievements: {e}")
        return {"achievements": [], "total_unlocked": 0}

# ========== UTILIDADES ==========

def mark_onboarding_seen(user_id: str) -> Dict:
    """Marca el onboarding como visto"""
    try:
        supabase.table("users_profile").update({
            "onboarding_seen": True,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", user_id).execute()
        
        return {"message": "Onboarding marked as seen"}
        
    except Exception as e:
        print(f"❌ Error marking onboarding: {e}")
        raise Exception(f"Failed to mark onboarding: {str(e)}")