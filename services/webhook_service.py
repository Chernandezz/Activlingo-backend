# services/webhook_service.py - NUEVO ARCHIVO
from datetime import datetime, timedelta, timezone
from typing import Dict
from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def log_subscription_event(user_id: str, subscription_id: str, event_type: str, details: Dict) -> None:
    """Registra eventos de suscripción para auditoría"""
    try:
        event_data = {
            "user_id": user_id,
            "subscription_id": str(subscription_id) if subscription_id else None,
            "event_type": event_type,
            "details": details,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        supabase.table("subscription_events").insert(event_data).execute()
        print(f"✅ Evento registrado: {event_type} para usuario {user_id}")
        
    except Exception as e:
        print(f"❌ Error registrando evento: {e}")

def process_subscription_event(event_type: str, data: Dict) -> Dict:
    """Procesa eventos de suscripción y registra auditoría"""
    try:
        from services.subscription_service import handle_stripe_webhook
        
        # Procesar el evento
        result = handle_stripe_webhook(event_type, data)
        
        # Registrar en auditoría si es exitoso
        if result.get("success"):
            user_id = data.get("metadata", {}).get("user_id")
            subscription_id = data.get("id") or data.get("subscription")
            
            if user_id:
                log_subscription_event(
                    user_id=user_id,
                    subscription_id=subscription_id,
                    event_type=event_type,
                    details={
                        "status": "processed", 
                        "stripe_data": {
                            "id": data.get("id"),
                            "status": data.get("status"),
                            "customer": data.get("customer")
                        }
                    }
                )
        
        return result
        
    except Exception as e:
        print(f"❌ Error procesando evento {event_type}: {e}")
        
        # Intentar registrar el error
        try:
            user_id = data.get("metadata", {}).get("user_id")
            if user_id:
                log_subscription_event(
                    user_id=user_id,
                    subscription_id=data.get("id"),
                    event_type=f"{event_type}_error",
                    details={"error": str(e), "data": data}
                )
        except:
            pass
            
        return {"success": False, "error": str(e)}

def get_subscription_events(user_id: str, limit: int = 50) -> Dict:
    """Obtiene el historial de eventos de suscripción de un usuario"""
    try:
        result = (
            supabase.table("subscription_events")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        
        return {
            "success": True,
            "events": result.data or [],
            "total": len(result.data) if result.data else 0
        }
        
    except Exception as e:
        print(f"❌ Error obteniendo eventos: {e}")
        return {"success": False, "error": str(e), "events": []}

def cleanup_old_events(days_old: int = 90) -> Dict:
    """Limpia eventos antiguos (usar en tarea programada)"""
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
        
        result = (
            supabase.table("subscription_events")
            .delete()
            .lt("created_at", cutoff_date.isoformat())
            .execute()
        )
        
        deleted_count = len(result.data) if result.data else 0
        
        return {
            "success": True,
            "message": f"Eliminados {deleted_count} eventos antiguos",
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        print(f"❌ Error limpiando eventos: {e}")
        return {"success": False, "error": str(e)}