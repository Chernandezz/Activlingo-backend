from fastapi import APIRouter, Depends
from services.user_service import is_trial_active, mark_onboarding_seen
from dependencies.auth import get_current_user
from uuid import UUID

user_router = APIRouter()

@user_router.get("/trial-status")
def check_trial_status(user_id: UUID = Depends(get_current_user)):
    return is_trial_active(user_id)

@user_router.post("/onboarding-seen")
def mark_seen(user_id: UUID = Depends(get_current_user)):
    return mark_onboarding_seen(user_id)
