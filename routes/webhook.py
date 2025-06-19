# routes/webhook.py - MEJORADO
import os
import stripe
from dotenv import load_dotenv
from fastapi import APIRouter, Request, Header, HTTPException
from starlette.responses import JSONResponse
from services.webhook_service import process_subscription_event

load_dotenv()

webhook_router = APIRouter()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

@webhook_router.post("/stripe")
async def stripe_webhook_handler(
    request: Request, 
    stripe_signature: str = Header(None, alias="Stripe-Signature")
):
    """Maneja webhooks de Stripe con auditoría completa"""
    payload = await request.body()
    
    # Log del webhook recibido
    print(f"📦 Webhook recibido desde Stripe")

    # Verificar que tenemos el secret configurado
    if not WEBHOOK_SECRET:
        print("❌ STRIPE_WEBHOOK_SECRET no configurado")
        return JSONResponse(
            content={"status": "error", "message": "Webhook secret not configured"}, 
            status_code=200
        )

    try:
        # Verificar firma del webhook
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=stripe_signature,
            secret=WEBHOOK_SECRET
        )
    except ValueError as e:
        print(f"❌ Payload inválido: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        print(f"❌ Firma inválida: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event["type"]
    event_data = event["data"]["object"]
    
    print(f"📦 Procesando webhook: {event_type}")

    try:
        # Procesar el evento usando el servicio de webhooks
        result = process_subscription_event(event_type, event_data)
        
        if result.get("success"):
            print(f"✅ Webhook {event_type} procesado exitosamente")
            return JSONResponse(
                content={
                    "status": "success", 
                    "message": result.get("message", "Event processed"),
                    "event_type": event_type
                }, 
                status_code=200
            )
        else:
            print(f"⚠️ Error procesando webhook {event_type}: {result.get('error')}")
            return JSONResponse(
                content={
                    "status": "error", 
                    "message": result.get("error", "Processing failed"),
                    "event_type": event_type
                }, 
                status_code=200  # Retornar 200 para evitar reintento de Stripe
            )
            
    except Exception as e:
        print(f"❌ Error crítico en webhook {event_type}: {e}")
        return JSONResponse(
            content={
                "status": "error", 
                "message": "Internal server error",
                "event_type": event_type
            }, 
            status_code=200  # Retornar 200 para evitar reintento de Stripe
        )

@webhook_router.get("/test")
def test_webhook_endpoint():
    """Endpoint de prueba para verificar que los webhooks funcionan"""
    return {
        "status": "ok",
        "message": "Webhook endpoint is working",
        "webhook_secret_configured": WEBHOOK_SECRET is not None,
        "stripe_key_configured": stripe.api_key is not None
    }