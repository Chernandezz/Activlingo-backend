from supabase import create_client, Client
import os
from dotenv import load_dotenv
from schemas.auth import AuthResponse


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def signup_user(email: str, password: str) -> AuthResponse | dict:
    try:
        response = supabase.auth.sign_up({"email": email, "password": password})

        # .session y .user son objetos, no diccionarios
        return AuthResponse(
            session=response.session.model_dump() if response.session else None,
            user=response.user.model_dump() if response.user else None
        )
    except Exception as e:
        return {"error": str(e)}



def login_user(email: str, password: str):
    try:
        result = supabase.auth.sign_in_with_password({"email": email, "password": password})

        return AuthResponse(
            session=result.session.model_dump() if result.session else None,
            user=result.user.model_dump() if result.user else None,
        )
    except Exception as e:
        print("Error en login_user:", e)
        return {"error": str(e)}


def logout_user(access_token: str) -> dict:
    try:
        temp_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        temp_client.auth.session = {"access_token": access_token}
        temp_client.auth.sign_out()
        return {"success": True}
    except Exception as e:
        return {"error": str(e), "success": False}

