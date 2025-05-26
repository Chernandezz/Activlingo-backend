from fastapi import APIRouter, HTTPException
from schemas.auth import SignUpRequest, LoginRequest, AuthResponse
from services.auth_service import signup_user, login_user, logout_user

auth_router = APIRouter()

@auth_router.post("/signup")
def signup(data: SignUpRequest):
    result = signup_user(data.email, data.password)

    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return {
        "success": True,
        "message": "User created successfully",
        "user": result.user  # Esto solo se accede si no es dict
    }


@auth_router.post("/login")
def login(data: LoginRequest):
    result = login_user(data.email, data.password)

    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=401, detail=result["error"])

    return {
        "success": True,
        "access_token": result.session.get("access_token"),
        "refresh_token": result.session.get("refresh_token"),
        "expires_in": result.session.get("expires_in"),
        "user": result.user
    }


@auth_router.post("/logout")
def logout(token: str):
    result = logout_user(token)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Logout failed"))
    return {"success": True, "message": "Logged out successfully"}
