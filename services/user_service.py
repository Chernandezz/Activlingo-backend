from datetime import datetime, timedelta, timezone
from supabase import create_client, Client
import os
from dotenv import load_dotenv


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)



def is_trial_active(user_id: str) -> dict:
    try:
        result = (
            supabase.table("users_profile")
            .select("*")
            .eq("id", user_id)
            .single()
            .execute()
        )
        profile = result.data

        if not profile:
            # Si no existe el perfil, devolvemos un “trial cerrado”
            return {
                "trial_end": None,
                "trial_active": False,
                "is_subscribed": False,
            }

        # parseamos trial_start (supabase lo da como ISO Zulu)
        trial_start = datetime.fromisoformat(profile["trial_start"].replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        # calculamos si ya expiró los 3 días
        expired = now > trial_start + timedelta(days=3)

        return {
            "trial_end": (trial_start + timedelta(days=3)).isoformat(),
            "trial_active": not expired,
            "is_subscribed": profile.get("is_subscribed", False),
        }

    except Exception as e:
        return {
            "trial_end": None,
            "trial_active": False,
            "is_subscribed": False,
            "error": str(e),
        }
def activate_subscription(user_id: str):
    supabase.table("users_profile").update({"is_subscribed": True}).eq("id", user_id).execute()
