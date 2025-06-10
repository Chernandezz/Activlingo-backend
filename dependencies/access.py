from fastapi import Depends, HTTPException, status
from services.user_service import is_trial_active

async def check_access(user_id: str):
    """
    Verifica si el usuario tiene acceso premium (trial activo o suscripción activa).
    """
    result = is_trial_active(user_id)

    if not result["trial_active"] and not result["is_subscribed"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You must be subscribed or have an active trial."
        )
