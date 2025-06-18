# routes/auth.py - CORREGIDO
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, EmailStr
from typing import Optional
from services.auth_service import signup_user, login_user, logout_user, get_user_from_token

auth_router = APIRouter()

# ========== MODELOS ==========

class SignUpRequest(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# ========== ENDPOINTS DE AUTENTICACIÓN ==========

@auth_router.post("/signup")
def signup_endpoint(request: SignUpRequest):
    """Endpoint de registro de usuario"""
    try:
        result = signup_user(
            email=request.email, 
            password=request.password,
            name=request.name
        )
        
        if result.get("success"):
            return {
                "success": True,
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
    """Endpoint de login de usuario"""
    try:
        result = login_user(email=request.email, password=request.password)
        
        if result.get("success"):
            return {
                "success": True,
                "message": "Login exitoso",
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
    """Endpoint de logout de usuario"""
    try:
        result = logout_user(token)
        
        return {
            "success": True,
            "message": result.get("message", "Logout exitoso")
        }
            
    except Exception as e:
        print(f"⚠️ Error en logout endpoint: {e}")
        # Siempre retornar éxito en logout para que el frontend limpie tokens
        return {
            "success": True,
            "message": "Logout completado"
        }

@auth_router.get("/me")
def get_current_user_info(token: str = Query(..., description="Access token")):
    """Obtiene información del usuario actual"""
    try:
        result = get_user_from_token(token)
        
        if result.get("success"):
            return {
                "success": True,
                "user": result.get("user")
            }
        else:
            raise HTTPException(status_code=401, detail="Token inválido")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting current user: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@auth_router.get("/verify")
def verify_token(token: str = Query(..., description="Access token")):
    """Verifica si un token es válido"""
    try:
        result = get_user_from_token(token)
        
        if result.get("success"):
            return {
                "valid": True,
                "user": result.get("user")
            }
        else:
            return {
                "valid": False,
                "error": result.get("error")
            }
            
    except Exception as e:
        print(f"❌ Error verifying token: {e}")
        return {
            "valid": False,
            "error": "Token verification failed"
        }