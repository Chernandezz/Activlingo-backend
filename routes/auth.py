# routes/auth.py - CORREGIDO
from fastapi import APIRouter, HTTPException
from schemas.auth import SignUpRequest, LoginRequest, AuthResponse
from services.auth_service import signup_user, login_user, logout_user

auth_router = APIRouter()

@auth_router.post("/signup")
def signup(data: SignUpRequest):
    """Endpoint de registro de usuario"""
    result = signup_user(data.email, data.password)

    # Verificar si hay error en el resultado
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    # Verificar si el signup fue exitoso
    if isinstance(result, dict) and result.get("success"):
        return {
            "success": True,
            "message": result.get("message", "User created successfully"),
            "user": result.get("user"),  # Acceder como diccionario
            "session": result.get("session")
        }
    else:
        # Si no es exitoso pero tampoco hay error explícito
        raise HTTPException(status_code=400, detail="Failed to create user")


@auth_router.post("/login")
def login(data: LoginRequest):
    """Endpoint de login de usuario"""
    result = login_user(data.email, data.password)

    # Verificar si hay error en el resultado
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=401, detail=result["error"])

    # Verificar si el login fue exitoso
    if isinstance(result, dict) and result.get("success"):
        return {
            "success": True,
            "access_token": result.get("access_token"),
            "refresh_token": result.get("refresh_token"),
            "user": result.get("user"),
            "session": result.get("session"),
            "profile": result.get("profile")
        }
    else:
        # Si no es exitoso pero tampoco hay error explícito
        raise HTTPException(status_code=401, detail="Invalid credentials")


@auth_router.post("/logout")
def logout(token: str):
    """Endpoint de logout de usuario"""
    result = logout_user(token)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Logout failed"))
    
    return {"success": True, "message": "Logged out successfully"}