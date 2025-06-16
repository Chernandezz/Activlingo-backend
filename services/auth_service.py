# services/auth_service.py - CORREGIDO
from supabase import create_client, Client
import os
from dotenv import load_dotenv
from typing import Dict, Any

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
            # Crear perfil en users_profile
            from services.user_service import create_default_profile
            from uuid import UUID
            create_default_profile(UUID(response.user.id))

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
            return {"error": "User already registered", "success": False}
        elif "Invalid email" in error_msg:
            return {"error": "Invalid email", "success": False}
        elif "Password should be at least" in error_msg:
            return {"error": "Password should be at least 6 characters", "success": False}
        else:
            return {"error": error_msg, "success": False}


def login_user(email: str, password: str) -> Dict[str, Any]:
    """Inicia sesión de usuario"""
    try:
        result = supabase.auth.sign_in_with_password({
            "email": email, 
            "password": password
        })

        if not result.session or not result.user:
            return {"error": "Invalid login credentials", "success": False}

        # Asegurar que el perfil existe
        from services.user_service import get_user_profile
        from uuid import UUID
        profile = get_user_profile(UUID(result.user.id))

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
            return {"error": "Invalid login credentials", "success": False}
        elif "Email not confirmed" in error_msg:
            return {"error": "Email not confirmed", "success": False}
        else:
            return {"error": error_msg, "success": False}


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
            return {"error": "Invalid token", "success": False}
            
    except Exception as e:
        print(f"❌ Error getting user from token: {e}")
        return {"error": str(e), "success": False}


# routes/auth.py - ROUTES CORREGIDAS
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, EmailStr
from typing import Optional
from services.auth_service import signup_user, login_user, logout_user

auth_router = APIRouter()

class SignUpRequest(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

@auth_router.post("/signup")
def signup_endpoint(request: SignUpRequest):
    """Endpoint de registro"""
    try:
        result = signup_user(
            email=request.email, 
            password=request.password,
            name=request.name
        )
        
        if result.get("success"):
            return {
                "message": "Usuario registrado exitosamente. Revisa tu email para confirmar.",
                "user": result.get("user"),
                "session": result.get("session")
            }
        else:
            raise HTTPException(
                status_code=400, 
                detail=result.get("error", "Error en el registro")
            )
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error en signup endpoint: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@auth_router.post("/login")
def login_endpoint(request: LoginRequest):
    """Endpoint de login"""
    try:
        result = login_user(email=request.email, password=request.password)
        
        if result.get("success"):
            return {
                "access_token": result.get("access_token"),
                "refresh_token": result.get("refresh_token"),
                "user": result.get("user"),
                "session": result.get("session"),
                "profile": result.get("profile")
            }
        else:
            raise HTTPException(
                status_code=401, 
                detail=result.get("error", "Credenciales inválidas")
            )
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error en login endpoint: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@auth_router.post("/logout")
def logout_endpoint(token: str = Query(..., description="Access token")):
    """Endpoint de logout"""
    try:
        result = logout_user(token)
        
        if result.get("success"):
            return {"message": "Logout exitoso"}
        else:
            return {"message": "Logout completado"} # Siempre éxito en logout
            
    except Exception as e:
        print(f"⚠️ Error en logout endpoint: {e}")
        return {"message": "Logout completado"} # Siempre éxito en logout


@auth_router.get("/me")
def get_current_user_info(token: str = Query(..., description="Access token")):
    """Obtiene información del usuario actual"""
    try:
        from services.auth_service import get_user_from_token
        result = get_user_from_token(token)
        
        if result.get("success"):
            return result.get("user")
        else:
            raise HTTPException(status_code=401, detail="Token inválido")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting current user: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")