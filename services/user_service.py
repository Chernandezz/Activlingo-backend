# services/user_service.py - CON CÁLCULO DINÁMICO
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
    """Obtiene el perfil completo del usuario con estadísticas dinámicas"""
    try:
        user_id_str = str(user_id)
        
        # Obtener usuario de auth
        auth_user = supabase.auth.admin.get_user_by_id(user_id_str)
        
        # Obtener o crear perfil básico
        profile = get_or_create_profile(user_id)
        
        # Calcular estadísticas dinámicamente
        stats = calculate_user_stats_dynamic(user_id)
        
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

# ========== ESTADÍSTICAS DINÁMICAS ==========

def calculate_user_stats_dynamic(user_id: UUID) -> Dict:
    """Calcula todas las estadísticas dinámicamente desde las tablas fuente"""
    try:
        user_id_str = str(user_id)
        now = datetime.now(timezone.utc)
        
        # Obtener fecha de registro del usuario
        join_date = get_user_join_date(user_id)
        
        # 1. CONVERSACIONES TOTALES
        total_conversations = count_user_conversations(user_id_str)
        
        # 2. CONVERSACIONES ESTE MES
        conversations_this_month = count_conversations_this_month(user_id_str, now)
        
        # 3. PALABRAS TOTALES APRENDIDAS
        total_words_learned = count_total_words_learned(user_id_str)
        
        # 4. PALABRAS ESTE MES
        words_this_month = count_words_this_month(user_id_str, now)
        
        # 5. ÚLTIMA ACTIVIDAD
        last_activity = get_last_activity(user_id_str)
        
        # 6. RACHA ACTUAL Y MÁXIMA
        streak_data = calculate_user_streaks(user_id_str, now)
        
        
        return {
            "total_conversations": total_conversations,
            "current_streak": streak_data["current_streak"],
            "longest_streak": streak_data["longest_streak"],
            "total_words_learned": total_words_learned,
            "join_date": join_date,
            "last_activity": last_activity,
            "conversations_this_month": conversations_this_month,
            "words_learned_this_month": words_this_month
        }
        
    except Exception as e:
        print(f"❌ Error calculating dynamic stats: {e}")
        return get_default_stats()

def count_user_conversations(user_id_str: str) -> int:
    """Cuenta total de conversaciones del usuario"""
    try:
        result = (
            supabase.table("chats")
            .select("id", count="exact")
            .eq("user_id", user_id_str)
            .execute()
        )
        return result.count or 0
    except Exception as e:
        print(f"❌ Error counting conversations: {e}")
        return 0

def count_conversations_this_month(user_id_str: str, now: datetime) -> int:
    """Cuenta conversaciones creadas este mes"""
    try:
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        result = (
            supabase.table("chats")
            .select("id", count="exact")
            .eq("user_id", user_id_str)
            .gte("created_at", start_of_month.isoformat())
            .execute()
        )
        return result.count or 0
    except Exception as e:
        print(f"❌ Error counting conversations this month: {e}")
        return 0

def count_total_words_learned(user_id_str: str) -> int:
    """Cuenta total de palabras en el diccionario del usuario"""
    try:
        result = (
            supabase.table("user_dictionary")
            .select("id", count="exact")
            .eq("user_id", user_id_str)
            .execute()
        )
        return result.count or 0
    except Exception as e:
        print(f"❌ Error counting total words: {e}")
        return 0

def count_words_this_month(user_id_str: str, now: datetime) -> int:
    """Cuenta palabras aprendidas este mes"""
    try:
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        result = (
            supabase.table("user_dictionary")
            .select("id", count="exact")
            .eq("user_id", user_id_str)
            .gte("created_at", start_of_month.isoformat())
            .execute()
        )
        return result.count or 0
    except Exception as e:
        print(f"❌ Error counting words this month: {e}")
        return 0

def get_last_activity(user_id_str: str) -> str:
    """Obtiene la fecha de última actividad (último chat o palabra agregada)"""
    try:
        # Último chat
        last_chat = (
            supabase.table("chats")
            .select("created_at")
            .eq("user_id", user_id_str)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        
        # Última palabra
        last_word = (
            supabase.table("user_dictionary")
            .select("created_at")
            .eq("user_id", user_id_str)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        
        dates = []
        if last_chat.data:
            dates.append(last_chat.data[0]["created_at"])
        if last_word.data:
            dates.append(last_word.data[0]["created_at"])
        
        if dates:
            return max(dates)
        
        return datetime.now(timezone.utc).isoformat()
        
    except Exception as e:
        print(f"❌ Error getting last activity: {e}")
        return datetime.now(timezone.utc).isoformat()

def calculate_user_streaks(user_id_str: str, now: datetime) -> Dict:
    """Calcula racha actual y máxima basado en días con actividad"""
    try:
        # Obtener todas las fechas de actividad (chats creados)
        result = (
            supabase.table("chats")
            .select("created_at")
            .eq("user_id", user_id_str)
            .order("created_at", desc=False)
            .execute()
        )
        
        if not result.data:
            return {"current_streak": 0, "longest_streak": 0}
        
        # Convertir a fechas y obtener días únicos
        activity_dates = set()
        for chat in result.data:
            date = datetime.fromisoformat(chat["created_at"].replace("Z", "+00:00"))
            activity_dates.add(date.date())
        
        # Ordenar fechas
        sorted_dates = sorted(list(activity_dates))
        
        if not sorted_dates:
            return {"current_streak": 0, "longest_streak": 0}
        
        # Calcular racha actual
        current_streak = 0
        today = now.date()
        yesterday = today - timedelta(days=1)
        
        # Verificar si hay actividad hoy o ayer
        if today in activity_dates or yesterday in activity_dates:
            current_streak = 1
            check_date = yesterday if yesterday in activity_dates else today
            
            # Contar días consecutivos hacia atrás
            for i in range(1, len(sorted_dates)):
                prev_date = check_date - timedelta(days=i)
                if prev_date in activity_dates:
                    current_streak += 1
                else:
                    break
        
        # Calcular racha máxima
        longest_streak = 1
        temp_streak = 1
        
        for i in range(1, len(sorted_dates)):
            if (sorted_dates[i] - sorted_dates[i-1]).days == 1:
                temp_streak += 1
                longest_streak = max(longest_streak, temp_streak)
            else:
                temp_streak = 1
        
        return {
            "current_streak": current_streak,
            "longest_streak": longest_streak
        }
        
    except Exception as e:
        print(f"❌ Error calculating streaks: {e}")
        return {"current_streak": 0, "longest_streak": 0}


def get_user_join_date(user_id: UUID) -> str:
    """Obtiene la fecha de registro del usuario"""
    try:
        # Intentar desde el perfil
        result = (
            supabase.table("users_profile")
            .select("created_at")
            .eq("id", str(user_id))
            .execute()
        )
        
        if result.data and result.data[0].get("created_at"):
            return result.data[0]["created_at"]
        
        # Si no, desde auth
        auth_user = supabase.auth.admin.get_user_by_id(str(user_id))
        if auth_user and auth_user.user:
            return str(auth_user.user.created_at)
        
        return datetime.now(timezone.utc).isoformat()
        
    except Exception as e:
        print(f"❌ Error getting join date: {e}")
        return datetime.now(timezone.utc).isoformat()

def get_default_stats() -> Dict:
    """Retorna estadísticas por defecto"""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "total_conversations": 0,
        "current_streak": 0,
        "longest_streak": 0,
        "total_words_learned": 0,
        "join_date": now,
        "last_activity": now,
        "conversations_this_month": 0,
        "words_learned_this_month": 0
    }

# ========== FUNCIÓN SIMPLIFICADA PARA ESTADÍSTICAS ==========

def get_user_stats(user_id: UUID) -> Dict:
    """Función simplificada que solo retorna estadísticas dinámicas"""
    return calculate_user_stats_dynamic(user_id)

# ========== SUSCRIPCIONES (SIN CAMBIOS) ==========

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

# ========== TRIAL (SIN CAMBIOS) ==========

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

# ========== LOGROS (SIN CAMBIOS) ==========

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

# ========== UTILIDADES (SIN CAMBIOS) ==========

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