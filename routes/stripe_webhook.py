import os
import stripe
from dotenv import load_dotenv
from fastapi import APIRouter, Request, Header, HTTPException
from starlette.responses import JSONResponse

from services.user_service import activate_subscription

load_dotenv()  # Cargar .env

router = APIRouter()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

@router.post("/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None, alias="Stripe-Signature")):
    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=stripe_signature,
            secret=WEBHOOK_SECRET
        )
    except ValueError as e:
        print("❌ Payload inválido")
        raise HTTPException(status_code=400, detail=str(e))
    except stripe.error.SignatureVerificationError as e:
        print("❌ Firma inválida")
        raise HTTPException(status_code=400, detail=str(e))

    print("📦 Evento recibido:", event["type"])

    if event["type"] == "payment_intent.succeeded":
        print("✅ Pago exitoso")

    elif event["type"] == "checkout.session.completed":
      session = event["data"]["object"]
      user_id = session["metadata"].get("user_id")

      if user_id:
          activate_subscription(user_id)
          print("✅ Suscripción activada para:", user_id)
      else:
          print("⚠️ No se encontró user_id en metadata")

    elif event["type"] == "invoice.payment_failed":
        print("❌ Falló el pago")

    return JSONResponse(content={"status": "success"}, status_code=200)
