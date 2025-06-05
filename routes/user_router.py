from fastapi import Depends
from fastapi import APIRouter
from services.user_service import is_trial_active

user_router = APIRouter()

@user_router.get("/trial-status")
def check_trial_status(user_id: str):
    return is_trial_active(user_id)
