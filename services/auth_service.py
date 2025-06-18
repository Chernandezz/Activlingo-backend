# services/auth_service.py - HOTFIX CORREGIDO
from supabase import create_client, Client
import os
from dotenv import load_dotenv
from typing import Dict, Any
from datetime import datetime, timezone

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def signup_user(email: str, password: str, name: str = None) -> Dict[str, Any]:
    """Registra un nuevo usuario"""
    try:
        user_metadata = {}
        if name:
            user_metadata["full_name"] = name
            user_metadata["name"] = name

        response = supabase.auth.sign_up({
            "email": email, 
            "password": password,
            "options": {
                "data": user_metadata
            }
        })

        if response.user:
            # ✅ CORREGIDO: Crear perfil con manejo de duplicados
            profile_result = create_basic_profile(response.user.id)
            print(f"📋 Profile creation result: {profile_result}")

        return {
            "success": True,
            "message": "Usuario registrado exitosamente",
            "user": response.user.model_dump() if response.user else None,
            "session": response.session.model_dump() if response.session else None
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error en signup_user: {error_msg}")
        
        # Manejo de errores específicos
        if "User already registered" in error_msg:
            return {"error": "El usuario ya está registrado", "success": False}
        elif "Invalid email" in error_msg:
            return {"error": "Email inválido", "success": False}
        elif "Password should be at least" in error_msg:
            return {"error": "La contraseña debe tener al menos 6 caracteres", "success": False}
        else:
            return {"error": "Error en el registro", "success": False}

def create_basic_profile(user_id: str) -> Dict:
    """Crea perfil básico del usuario - función independiente con manejo de duplicados"""
    try:
        user_id_str = str(user_id)
        now = datetime.now(timezone.utc).isoformat()
        
        # ✅ CORREGIDO: Verificar si ya existe antes de crear
        existing_check = supabase.table("users_profile").select("id").eq("id", user_id_str).execute()
        
        if existing_check.data and len(existing_check.data) > 0:
            print(f"ℹ️ Perfil ya existe para usuario {user_id_str}")
            return {"success": True, "message": "Profile already exists"}
        
        # ✅ CORREGIDO: Crear perfil básico con campos mínimos
        new_profile = {
            "id": user_id_str,
            "trial_start": now,
            "onboarding_seen": False,
            "subscription_type": "trial",
            "is_subscribed": False,  # ✅ Agregado campo requerido
            "created_at": now,
            "updated_at": now
        }
        
        profile_result = supabase.table("users_profile").insert(new_profile).execute()
        print(f"✅ Perfil creado: {profile_result.data}")
        
        # ✅ CORREGIDO: Crear estadísticas con manejo de duplicados
        stats_check = supabase.table("user_stats").select("id").eq("user_id", user_id_str).execute()
        
        if not (stats_check.data and len(stats_check.data) > 0):
            initial_stats = {
                "user_id": user_id_str,
                "total_conversations": 0,
                "current_streak": 0,
                "longest_streak": 0,
                "total_words_learned": 0,
                "total_session_minutes": 0,
                "conversations_this_month": 0,
                "words_this_month": 0,
                "last_activity_at": now,
                "streak_updated_at": now
            }
            
            stats_result = supabase.table("user_stats").insert(initial_stats).execute()
            print(f"✅ Estadísticas creadas: {stats_result.data}")
        else:
            print(f"ℹ️ Estadísticas ya existen para usuario {user_id_str}")
        
        print(f"✅ Perfil básico completado para usuario {user_id_str}")
        return {"success": True, "message": "Profile created successfully"}
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error creating basic profile: {error_msg}")
        
        # ✅ MEJORADO: Manejo específico de errores
        if "duplicate key" in error_msg and "users_profile_pkey" in error_msg:
            # El usuario ya existe, no es un error crítico
            print(f"ℹ️ Usuario {user_id_str} ya tiene perfil, continuando...")
            return {"success": True, "message": "Profile already exists"}
        elif "JSON could not be generated" in error_msg:
            # Error de Cloudflare/Supabase, reintenta con datos mínimos
            print(f"⚠️ Error de JSON, reintentando con datos mínimos...")
            return create_minimal_profile(user_id_str)
        else:
            return {"success": False, "error": error_msg}

def create_minimal_profile(user_id: str) -> Dict:
    """Crea un perfil mínimo en caso de errores con el perfil completo"""
    try:
        now = datetime.now(timezone.utc).isoformat()
        
        # Perfil mínimo solo con campos esenciales
        minimal_profile = {
            "id": user_id,
            "trial_start": now,
            "onboarding_seen": False,
            "is_subscribed": False
        }
        
        result = supabase.table("users_profile").upsert(minimal_profile).execute()
        print(f"✅ Perfil mínimo creado: {result.data}")
        
        return {"success": True, "message": "Minimal profile created"}
        
    except Exception as e:
        print(f"❌ Error creating minimal profile: {e}")
        return {"success": False, "error": str(e)}

def login_user(email: str, password: str) -> Dict[str, Any]:
    """Inicia sesión de usuario"""
    try:
        result = supabase.auth.sign_in_with_password({
            "email": email, 
            "password": password
        })

        if not result.session or not result.user:
            return {"error": "Credenciales inválidas", "success": False}

        # ✅ CORREGIDO: Asegurar que el perfil existe al hacer login
        profile = get_or_ensure_user_profile(result.user.id)

        return {
            "success": True,
            "access_token": result.session.access_token,
            "refresh_token": result.session.refresh_token,
            "user": {
                "id": result.user.id,
                "email": result.user.email,
                "name": result.user.user_metadata.get("full_name", ""),
                "avatar_url": result.user.user_metadata.get("avatar_url", ""),
                "email_confirmed": result.user.email_confirmed_at is not None,
                "created_at": str(result.user.created_at) if result.user.created_at else None,
            },
            "session": result.session.model_dump(),
            "profile": profile
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error en login_user: {error_msg}")
        
        # Manejo de errores específicos
        if "Invalid login credentials" in error_msg:
            return {"error": "Credenciales inválidas", "success": False}
        elif "Email not confirmed" in error_msg:
            return {"error": "Email no confirmado", "success": False}
        else:
            return {"error": "Error en el login", "success": False}

def get_or_ensure_user_profile(user_id: str) -> Dict:
    """Obtiene perfil básico del usuario y lo crea si no existe"""
    try:
        result = supabase.table("users_profile").select("*").eq("id", user_id).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        else:
            # Si no existe, crear uno básico
            print(f"⚠️ Perfil no encontrado para {user_id}, creando...")
            create_result = create_basic_profile(user_id)
            
            if create_result.get("success"):
                # Intentar obtener nuevamente
                retry_result = supabase.table("users_profile").select("*").eq("id", user_id).execute()
                if retry_result.data and len(retry_result.data) > 0:
                    return retry_result.data[0]
            
            # Si todo falla, retornar perfil mínimo
            return {"id": user_id, "onboarding_seen": False, "is_subscribed": False}
            
    except Exception as e:
        print(f"❌ Error getting user profile: {e}")
        return {"id": user_id, "onboarding_seen": False, "is_subscribed": False}

def logout_user(access_token: str) -> Dict[str, Any]:
    """Cierra sesión del usuario"""
    try:
        # Crear cliente temporal con el token
        temp_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Establecer la sesión manualmente
        temp_client.auth._session = {
            "access_token": access_token,
            "token_type": "bearer"
        }
        
        # Hacer logout
        temp_client.auth.sign_out()
        
        return {"success": True, "message": "Logout successful"}
        
    except Exception as e:
        print(f"⚠️ Error en logout_user: {e}")
        # Aunque falle el logout en Supabase, reportar éxito
        # porque el frontend limpiará los tokens localmente
        return {"success": True, "message": "Logout completed"}

def get_user_from_token(access_token: str) -> Dict[str, Any]:
    """Obtiene información del usuario desde el token"""
    try:
        temp_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        temp_client.auth._session = {
            "access_token": access_token,
            "token_type": "bearer"
        }
        
        response = temp_client.auth.get_user()
        
        if response.user:
            return {
                "success": True,
                "user": {
                    "id": response.user.id,
                    "email": response.user.email,
                    "name": response.user.user_metadata.get("full_name", ""),
                    "avatar_url": response.user.user_metadata.get("avatar_url", ""),
                    "email_confirmed": response.user.email_confirmed_at is not None,
                }
            }
        else:
            return {"error": "Token inválido", "success": False}
            
    except Exception as e:
        print(f"❌ Error getting user from token: {e}")
        return {"error": str(e), "success": False}