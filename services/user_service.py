# services/user_service.py - VERSIÓN CON NUEVAS TABLAS
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

# ========== PERFIL Y ESTADÍSTICAS ==========


def get_full_user_profile(user_id: UUID) -> Dict:
    """Obtiene el perfil completo del usuario con estadísticas y suscripción - CORREGIDO"""
    try:
        user_id_str = str(user_id)
        
        # ✅ CORREGIDO: Timeout más largo para Supabase
        print(f"🔍 Getting profile for user: {user_id_str}")
        
        # Obtener información básica del usuario con timeout
        try:
            auth_user = supabase.auth.admin.get_user_by_id(user_id_str)
            print(f"✅ Auth user retrieved: {auth_user.user.email if auth_user.user else 'None'}")
        except Exception as auth_error:
            print(f"⚠️ Auth user retrieval failed: {auth_error}")
            auth_user = None
        
        # Obtener o crear perfil básico
        try:
            profile = get_or_create_basic_profile(user_id)
            print(f"✅ Profile retrieved: {profile.get('id', 'None')}")
        except Exception as profile_error:
            print(f"⚠️ Profile retrieval failed: {profile_error}")
            profile = {"id": user_id_str, "onboarding_seen": False}
        
        # Obtener estadísticas (con fallback)
        try:
            stats = get_user_stats(user_id)
            print(f"✅ Stats retrieved: {stats.get('total_conversations', 0)} conversations")
        except Exception as stats_error:
            print(f"⚠️ Stats retrieval failed: {stats_error}")
            stats = get_default_stats()
        
        # Obtener suscripción actual (con fallback)
        try:
            subscription = get_current_subscription(user_id)
            print(f"✅ Subscription retrieved: {subscription.get('status', 'None') if subscription else 'None'}")
        except Exception as sub_error:
            print(f"⚠️ Subscription retrieval failed: {sub_error}")
            subscription = None
        
        # ✅ CORREGIDO: Construir respuesta con datos seguros
        result = {
            "user": {
                "id": user_id_str,
                "email": auth_user.user.email if auth_user and auth_user.user else "",
                "name": auth_user.user.user_metadata.get("full_name", "") if auth_user and auth_user.user else "",
                "avatar_url": auth_user.user.user_metadata.get("avatar_url", "") if auth_user and auth_user.user else "",
                "created_at": str(auth_user.user.created_at) if auth_user and auth_user.user else "",
            },
            "stats": stats or get_default_stats(),
            "subscription": subscription
        }
        
        print(f"✅ Full profile assembled successfully for {user_id_str}")
        return result
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error getting full user profile: {error_msg}")
        
        # ✅ CORREGIDO: Retornar datos mínimos en lugar de error
        return {
            "user": {
                "id": str(user_id), 
                "email": "", 
                "name": "",
                "avatar_url": "",
                "created_at": ""
            },
            "stats": get_default_stats(),
            "subscription": None,
            "error": "Profile data partially unavailable"
        }

# ✅ AGREGAR: Función helper para manejo robusto de perfil
def get_or_create_basic_profile(user_id: UUID) -> Dict:
    """Obtiene o crea el perfil básico del usuario - VERSION ROBUSTA"""
    try:
        user_id_str = str(user_id)
        
        # Verificar si existe con timeout corto
        result = supabase.table("users_profile").select("*").eq("id", user_id_str).execute()
        
        if result.data and len(result.data) > 0:
            print(f"✅ Profile found for {user_id_str}")
            return result.data[0]
        
        print(f"⚠️ Profile not found for {user_id_str}, creating minimal profile...")
        
        # Crear perfil mínimo
        now = datetime.now(timezone.utc).isoformat()
        new_profile = {
            "id": user_id_str,
            "trial_start": now,
            "onboarding_seen": False,
            "is_subscribed": False,
            "created_at": now,
            "updated_at": now
        }
        
        # Usar upsert para evitar errores de duplicado
        result = supabase.table("users_profile").upsert(new_profile).execute()
        
        if result.data and len(result.data) > 0:
            print(f"✅ Profile created for {user_id_str}")
            return result.data[0]
        else:
            print(f"⚠️ Profile creation returned no data for {user_id_str}")
            return new_profile
        
    except Exception as e:
        print(f"❌ Error in get_or_create_basic_profile: {e}")
        # Retornar perfil mínimo en memoria
        return {
            "id": str(user_id), 
            "onboarding_seen": False, 
            "is_subscribed": False,
            "trial_start": datetime.now(timezone.utc).isoformat()
        }
    

def start_user_trial(user_id: UUID) -> Dict:
    """Activa el trial manualmente para el usuario"""
    try:
        # Validar que no tenga suscripción activa ni trial vigente
        # current = get_current_subscription(user_id)
        # if current and current.get("status") in ["active", "trial"]:
        #     return {
        #         "success": False,
        #         "message": "Ya tienes una suscripción activa o un trial vigente"
        #     }

        now = datetime.now(timezone.utc)
        trial_end = now + timedelta(days=3)

        supabase.table("users_profile").update({
            "trial_start": now.isoformat(),
            "onboarding_seen": True,
            "subscription_type": "trial",
            "updated_at": now.isoformat()
        }).eq("id", str(user_id)).execute()

        return {
            "success": True,
            "message": "Trial activado exitosamente",
            "trial_start": now.isoformat(),
            "trial_end": trial_end.isoformat()
        }

    except Exception as e:
        print(f"❌ Error al activar el trial: {e}")
        return {"success": False, "message": "Error interno"}


def get_or_create_basic_profile(user_id: UUID) -> Dict:
    """Obtiene o crea el perfil básico del usuario"""
    try:
        user_id_str = str(user_id)
        
        # Verificar si existe
        result = supabase.table("users_profile").select("*").eq("id", user_id_str).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        
        # Crear perfil básico
        new_profile = {
            "id": user_id_str,
            "trial_start": datetime.now(timezone.utc).isoformat(),
            "onboarding_seen": False,
        }
        
        result = supabase.table("users_profile").insert(new_profile).execute()
        
        # También crear estadísticas iniciales
        create_initial_user_stats(user_id)
        
        return result.data[0] if result.data else new_profile
        
    except Exception as e:
        print(f"❌ Error creating basic profile: {e}")
        return {"id": str(user_id), "onboarding_seen": False}

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
            # Crear estadísticas iniciales
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
    return {
        "total_conversations": 0,
        "current_streak": 0,
        "longest_streak": 0,
        "total_words_learned": 0,
        "average_session_minutes": 0,
        "join_date": datetime.now(timezone.utc).isoformat(),
        "last_activity": datetime.now(timezone.utc).isoformat(),
        "conversations_this_month": 0,
        "words_learned_this_month": 0
    }

def calculate_average_session(stats: Dict) -> int:
    """Calcula el promedio de minutos por sesión"""
    total_minutes = stats.get("total_session_minutes", 0)
    total_conversations = stats.get("total_conversations", 0)
    
    if total_conversations > 0:
        return int(total_minutes / total_conversations)
    
    return 0

# ========== SUSCRIPCIONES ==========

def get_current_subscription(user_id: UUID) -> Optional[Dict]:
    """Obtiene la suscripción actual del usuario o verifica el trial"""
    try:
        result = (
            supabase.table("user_subscriptions")
            .select("""
                *,
                subscription_plans(
                    id, name, slug, price, currency, billing_interval,
                    features, max_conversations_per_day, max_words_per_day,
                    priority_support
                )
            """)
            .eq("user_id", str(user_id))
            .eq("status", "active")
            .limit(1)
            .maybe_single()
            .execute()
        )

        # ✅ Validación defensiva contra None
        if result and result.data:
            sub = result.data
            plan = sub.get("subscription_plans", {})

            return {
                "id": sub.get("id"),
                "user_id": sub.get("user_id"),
                "plan": {
                    "id": plan.get("id"),
                    "name": plan.get("name"),
                    "slug": plan.get("slug"),
                    "price": plan.get("price"),
                    "currency": plan.get("currency"),
                    "billing_interval": plan.get("billing_interval"),
                    "features": plan.get("features", []),
                    "max_conversations": plan.get("max_conversations_per_day", -1),
                    "max_words_per_day": plan.get("max_words_per_day", -1),
                    "priority_support": plan.get("priority_support", False)
                },
                "status": sub.get("status"),
                "starts_at": sub.get("starts_at"),
                "ends_at": sub.get("ends_at"),
                "trial_ends_at": sub.get("trial_ends_at"),
                "canceled_at": sub.get("canceled_at")
            }

        # Si no hay suscripción activa, verificar el trial
        return check_trial_subscription(user_id)

    except Exception as e:
        print(f"❌ Error getting current subscription: {e}")
        return check_trial_subscription(user_id)


def check_trial_subscription(user_id: UUID) -> Optional[Dict]:
    """Verifica si el usuario tiene trial activo"""
    try:
        # Obtener información del trial desde users_profile
        profile_result = (
            supabase.table("users_profile")
            .select("trial_start")
            .eq("id", str(user_id))
            .single()
            .execute()
        )
        
        if profile_result.data and profile_result.data.get("trial_start"):
            trial_start = datetime.fromisoformat(
                profile_result.data["trial_start"].replace("Z", "+00:00")
            )
            trial_end = trial_start + timedelta(days=3)  # 3 días de trial
            now = datetime.now(timezone.utc)
            
            if now <= trial_end:
                # Obtener el plan básico para el trial
                basic_plan = get_plan_by_slug("trial")
                
                return {
                    "id": None,
                    "user_id": str(user_id),
                    "plan": basic_plan,
                    "status": "trial",
                    "starts_at": trial_start.isoformat(),
                    "ends_at": None,
                    "trial_ends_at": trial_end.isoformat(),
                    "canceled_at": None
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
                "max_conversations": plan.get("max_conversations_per_day", -1),
                "max_words_per_day": plan.get("max_words_per_day", -1),
                "priority_support": plan.get("priority_support", False),
                "stripe_price_id": plan.get("stripe_price_id")
            })
        
        return plans
        
    except Exception as e:
        print(f"❌ Error getting available plans: {e}")
        return []

def get_plan_by_slug(slug: str) -> Optional[Dict]:
    """Obtiene un plan por su slug"""
    try:
        result = (
            supabase.table("subscription_plans")
            .select("*")
            .eq("slug", slug)
            .eq("is_active", True)
            .single()
            .execute()
        )
        
        if result.data:
            plan = result.data
            return {
                "id": plan.get("id"),
                "name": plan.get("name"),
                "slug": plan.get("slug"),
                "price": plan.get("price"),
                "currency": plan.get("currency"),
                "billing_interval": plan.get("billing_interval"),
                "features": plan.get("features", []),
                "max_conversations": plan.get("max_conversations_per_day", -1),
                "max_words_per_day": plan.get("max_words_per_day", -1),
                "priority_support": plan.get("priority_support", False)
            }
        
        return None
        
    except Exception as e:
        print(f"❌ Error getting plan by slug: {e}")
        return None

# ========== LOGROS ==========

def get_user_achievements(user_id: UUID) -> Dict:
    """Obtiene todos los logros del usuario"""
    try:
        # Obtener todos los logros disponibles
        all_achievements = (
            supabase.table("achievements")
            .select("*")
            .eq("is_active", True)
            .execute()
        )
        
        # Obtener progreso del usuario
        user_progress = (
            supabase.table("user_achievements")
            .select("*")
            .eq("user_id", str(user_id))
            .execute()
        )
        
        # Crear diccionario de progreso
        progress_dict = {}
        for progress in user_progress.data:
            achievement_id = progress.get("achievement_id")
            progress_dict[achievement_id] = progress
        
        # Combinar información
        achievements = []
        total_unlocked = 0
        
        for achievement in all_achievements.data:
            achievement_id = achievement.get("id")
            user_progress_data = progress_dict.get(achievement_id, {})
            
            is_unlocked = user_progress_data.get("unlocked_at") is not None
            if is_unlocked:
                total_unlocked += 1
            
            achievements.append({
                "id": str(achievement_id),
                "title": achievement.get("title"),
                "description": achievement.get("description"),
                "icon": achievement.get("icon"),
                "category": achievement.get("category"),
                "target_value": achievement.get("target_value"),
                "current_progress": user_progress_data.get("current_progress", 0),
                "unlocked": is_unlocked,
                "unlocked_at": user_progress_data.get("unlocked_at")
            })
        
        return {
            "achievements": achievements,
            "total_unlocked": total_unlocked
        }
        
    except Exception as e:
        print(f"❌ Error getting user achievements: {e}")
        return {"achievements": [], "total_unlocked": 0}

# ========== ACTUALIZACIÓN DE PERFIL ==========

def update_user_profile(user_id: UUID, updates: Dict) -> Dict:
    """Actualiza el perfil del usuario"""
    try:
        # Actualizar users_profile si hay campos relevantes
        profile_updates = {}
        if "notifications" in updates:
            profile_updates["notifications_settings"] = updates["notifications"]
        
        if profile_updates:
            supabase.table("users_profile").update(profile_updates).eq("id", str(user_id)).execute()
        
        # Aquí puedes agregar lógica para actualizar otros campos como idioma, objetivo, etc.
        # en una tabla separada de preferencias si es necesario
        
        return {"success": True, "message": "Profile updated successfully"}
        
    except Exception as e:
        print(f"❌ Error updating user profile: {e}")
        return {"success": False, "error": str(e)}

# ========== FUNCIONES LEGACY (mantener compatibilidad) ==========

def get_user_profile(user_id: UUID) -> Dict:
    """Función legacy - mantener para compatibilidad"""
    return get_or_create_basic_profile(user_id)

def is_trial_active(user_id: UUID) -> Dict:
    """Verifica si el usuario está en periodo de prueba o suscripción"""
    try:
        result = (
            supabase.table("users_profile")
            .select("trial_start, onboarding_seen, is_subscribed, subscription_type")
            .eq("id", str(user_id))
            .maybe_single()
            .execute()
        )

        if not result.data:
            print("⚠️ Perfil no encontrado.")
            return {
                "trial_end": None,
                "trial_active": False,
                "is_subscribed": False,
                "onboarding_seen": False,
            }

        profile = result.data
        onboarding_seen = profile.get("onboarding_seen", False)
        is_subscribed = profile.get("is_subscribed", False)
        trial_start_str = profile.get("trial_start")
        subscription_type = profile.get("subscription_type")

        trial_active = False
        trial_end = None

        if trial_start_str and subscription_type == "trial":
            trial_start = datetime.fromisoformat(trial_start_str.replace("Z", "+00:00"))
            trial_end_dt = trial_start + timedelta(days=3)
            now = datetime.now(timezone.utc)

            if now <= trial_end_dt:
                trial_active = True
                trial_end = trial_end_dt.isoformat()

        return {
            "trial_end": trial_end,
            "trial_active": trial_active,
            "is_subscribed": is_subscribed,
            "onboarding_seen": onboarding_seen,
        }

    except Exception as e:
        print(f"❌ Error checking trial status: {e}")
        return {
            "trial_end": None,
            "trial_active": False,
            "is_subscribed": False,
            "onboarding_seen": False,
        }


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