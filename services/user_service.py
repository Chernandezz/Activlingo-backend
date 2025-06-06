from datetime import datetime, timedelta, timezone
from uuid import UUID
from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def is_trial_active(user_id: UUID) -> dict:
    try:
        result = (
            supabase.table("users_profile")
            .select("*")
            .eq("id", str(user_id))
            .execute()
        )

        if not result.data or len(result.data) == 0:
            return {
                "trial_end": None,
                "trial_active": False,
                "is_subscribed": False,
                "onboarding_seen": False,
            }

        profile = result.data[0]  # ✅ importante: accedemos al primer elemento

        trial_start_raw = profile.get("trial_start")
        if not trial_start_raw:
            return {
                "trial_end": None,
                "trial_active": False,
                "is_subscribed": profile.get("is_subscribed", False),
                "onboarding_seen": profile.get("onboarding_seen", False),
            }

        trial_start = datetime.fromisoformat(trial_start_raw.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        expired = now > trial_start + timedelta(days=3)

        return {
            "trial_end": (trial_start + timedelta(days=3)).isoformat(),
            "trial_active": not expired,
            "is_subscribed": profile.get("is_subscribed", False),
            "onboarding_seen": profile.get("onboarding_seen", False),
        }

    except Exception as e:
        return {
            "trial_end": None,
            "trial_active": False,
            "is_subscribed": False,
            "onboarding_seen": False,
            "error": str(e),
        }

def activate_subscription(user_id: str):
    supabase.table("users_profile").update({"is_subscribed": True}).eq("id", user_id).execute()

def mark_onboarding_seen(user_id: str):
    try:
        supabase.table("users_profile").update({"onboarding_seen": True}).eq("id", user_id).execute()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}
