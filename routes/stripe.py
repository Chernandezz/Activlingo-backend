from fastapi import APIRouter, HTTPException, Depends
from services.stripe_service import create_checkout_session
from dependencies.auth import get_current_user

stripe_router = APIRouter()

@stripe_router.post("/create-checkout-session")
def create_checkout(user_id: str = Depends(get_current_user)):
    try:
        url = create_checkout_session(user_id)
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
