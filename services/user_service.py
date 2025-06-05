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
        result = supabase.table("users_profile").select("*").eq("id", user_id).single().execute()
        profile = result.data

        if not profile:
            return {"trial_active": False, "reason": "User profile not found"}

        trial_start = datetime.fromisoformat(profile["trial_start"].replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        expired = now > trial_start + timedelta(days=3)

        return {
            "trial_active": not expired,
            "trial_end": (trial_start + timedelta(days=3)).isoformat(),
            "is_subscribed": profile["is_subscribed"]
        }

    except Exception as e:
        return {"trial_active": False, "error": str(e)}
