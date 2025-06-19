# services/subscription_service.py - COMPLETO Y LIMPIO
import os
import stripe
from datetime import datetime, timezone, timedelta
from uuid import UUID
from supabase import create_client, Client
from dotenv import load_dotenv
from typing import Dict, Optional, List
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:4200")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ========== CHECKOUT Y PAGOS ==========

def create_checkout_session(user_id: UUID, plan_slug: str, billing_interval: str = "monthly") -> Dict:
    """Crea una sesión de checkout de Stripe"""
    try:
        # Obtener el plan
        plan = get_plan_by_slug_and_interval(plan_slug, billing_interval)
        if not plan:
            return {"success": False, "error": "Plan not found"}
        
        stripe_price_id = plan.get("stripe_price_id")
        if not stripe_price_id:
            return {"success": False, "error": "Stripe price ID not configured"}
        
        # Obtener información del usuario
        user_id_str = str(user_id)
        auth_user = supabase.auth.admin.get_user_by_id(user_id_str)
        
        if not auth_user.user:
            return {"success": False, "error": "User not found"}
        
        # Crear o obtener customer de Stripe
        stripe_customer_id = get_or_create_stripe_customer(user_id_str, auth_user.user.email)
        
        # Crear sesión de checkout
        session = stripe.checkout.Session.create(
            customer=stripe_customer_id,
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{"price": stripe_price_id, "quantity": 1}],
            metadata={
                "user_id": user_id_str,
                "plan_id": str(plan["id"]),
                "plan_slug": plan_slug
            },
            success_url=f"{FRONTEND_URL}/profile?success=true&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/profile?canceled=true",
            allow_promotion_codes=True,
            subscription_data={
                "metadata": {
                    "user_id": user_id_str,
                    "plan_id": str(plan["id"])
                }
            }
        )
        
        print(f"✅ Checkout session created: {session.id}")
        
        return {
            "success": True,
            "checkout_url": session.url,
            "session_id": session.id
        }
        
    except stripe.error.StripeError as e:
        print(f"❌ Stripe error: {e}")
        return {"success": False, "error": f"Payment error: {str(e)}"}
    except Exception as e:
        print(f"❌ Error creating checkout: {e}")
        return {"success": False, "error": str(e)}

def get_or_create_stripe_customer(user_id: str, email: str) -> str:
    """Obtiene o crea un customer de Stripe"""
    try:
        # Verificar si ya existe
        existing = (
            supabase.table("user_subscriptions")
            .select("stripe_customer_id")
            .eq("user_id", user_id)
            .not_.is_("stripe_customer_id", "null")
            .limit(1)
            .execute()
        )
        
        if existing.data and existing.data[0].get("stripe_customer_id"):
            return existing.data[0]["stripe_customer_id"]
        
        # Crear nuevo customer
        customer = stripe.Customer.create(
            email=email,
            metadata={"user_id": user_id}
        )
        
        print(f"✅ New Stripe customer created: {customer.id}")
        return customer.id
        
    except Exception as e:
        print(f"❌ Error with Stripe customer: {e}")
        raise e

def cancel_subscription(user_id: UUID) -> Dict:
    """Cancela la suscripción actual del usuario"""
    try:
        # Obtener suscripción activa
        current_sub = (
            supabase.table("user_subscriptions")
            .select("*")
            .eq("user_id", str(user_id))
            .eq("status", "active")
            .single()
            .execute()
        )
        
        if not current_sub.data:
            return {"success": False, "error": "No active subscription found"}
        
        subscription_data = current_sub.data
        stripe_subscription_id = subscription_data.get("stripe_subscription_id")
        
        # Cancelar en Stripe
        if stripe_subscription_id:
            stripe_subscription = stripe.Subscription.modify(
                stripe_subscription_id,
                cancel_at_period_end=True
            )
            
            # Actualizar en base de datos
            supabase.table("user_subscriptions").update({
                "status": "canceled",
                "canceled_at": datetime.now(timezone.utc).isoformat(),
                "ends_at": datetime.fromtimestamp(
                    stripe_subscription.current_period_end, 
                    tz=timezone.utc
                ).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", subscription_data["id"]).execute()
            
            print(f"✅ Subscription canceled: {stripe_subscription_id}")
            
            return {
                "success": True,
                "message": "Subscription canceled successfully",
                "ends_at": datetime.fromtimestamp(
                    stripe_subscription.current_period_end, 
                    tz=timezone.utc
                ).isoformat()
            }
        else:
            # Si no hay stripe_subscription_id, solo actualizar en BD
            supabase.table("user_subscriptions").update({
                "status": "canceled",
                "canceled_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", subscription_data["id"]).execute()
            
            return {
                "success": True,
                "message": "Subscription canceled successfully",
                "ends_at": subscription_data.get("current_period_end")
            }
        
    except stripe.error.StripeError as e:
        print(f"❌ Stripe error canceling: {e}")
        return {"success": False, "error": f"Payment error: {str(e)}"}
    except Exception as e:
        print(f"❌ Error canceling subscription: {e}")
        return {"success": False, "error": str(e)}

# ========== ESTADO DE SUSCRIPCIÓN ==========

def get_user_subscription_status(user_id: UUID) -> Dict:
    """Obtiene el estado completo de suscripción del usuario"""
    try:
        from services.user_service import get_current_subscription
        
        subscription = get_current_subscription(user_id)
        access_info = get_user_plan_access(user_id)
        
        if not subscription:
            return {
                "status": "no_subscription",
                "message": "No tienes una suscripción activa",
                "subscription": None,
                "access": access_info,
                "can_upgrade": True,
                "can_cancel": False
            }
        
        status = subscription.get("status")
        
        status_info = {
            "trial": {"message": "Estás en período de prueba", "can_upgrade": True, "can_cancel": False},
            "active": {"message": "Suscripción activa", "can_upgrade": False, "can_cancel": True},
            "canceled": {"message": "Suscripción cancelada", "can_upgrade": True, "can_cancel": False}
        }
        
        info = status_info.get(status, {"message": "Estado desconocido", "can_upgrade": True, "can_cancel": False})
        
        return {
            "status": status,
            "message": info["message"],
            "subscription": subscription,
            "access": access_info,
            "can_upgrade": info["can_upgrade"],
            "can_cancel": info["can_cancel"]
        }
        
    except Exception as e:
        print(f"❌ Error getting subscription status: {e}")
        return {
            "status": "error",
            "message": "Error obteniendo estado",
            "subscription": None,
            "access": get_default_access(),
            "can_upgrade": False,
            "can_cancel": False
        }

def get_user_plan_access(user_id: UUID) -> Dict:
    """Obtiene la información de acceso del usuario"""
    try:
        from services.user_service import get_current_subscription
        
        subscription = get_current_subscription(user_id)
        
        if not subscription:
            return get_default_access()
        
        plan = subscription.get("plan", {})
        status = subscription.get("status")
        
        # Trial y active tienen acceso premium
        has_premium = status in ["active", "trial"] and plan.get("slug") != "basic"
        
        return {
            "plan_slug": plan.get("slug", "basic"),
            "has_premium": has_premium,
            "max_conversations_per_day": -1 if has_premium else 5,
            "max_words_per_day": -1 if has_premium else 50,
            "priority_support": has_premium,
            "status": status
        }
        
    except Exception as e:
        print(f"❌ Error getting plan access: {e}")
        return get_default_access()

def get_default_access() -> Dict:
    """Retorna acceso por defecto (básico)"""
    return {
        "plan_slug": "basic",
        "has_premium": False,
        "max_conversations_per_day": 5,
        "max_words_per_day": 50,
        "priority_support": False,
        "status": "basic"
    }

# ========== UTILIDADES ==========

def get_plan_by_slug_and_interval(slug: str, billing_interval: str) -> Optional[Dict]:
    """Obtiene un plan por slug e intervalo de facturación"""
    try:
        result = (
            supabase.table("subscription_plans")
            .select("*")
            .eq("slug", slug)
            .eq("billing_interval", billing_interval)
            .eq("is_active", True)
            .single()
            .execute()
        )
        
        return result.data if result.data else None
        
    except Exception as e:
        print(f"❌ Error getting plan: {e}")
        return None

# ========== WEBHOOKS ==========

def handle_stripe_webhook(event_type: str, data: Dict) -> Dict:
    """Maneja los webhooks de Stripe"""
    try:
        print(f"🔄 Processing webhook: {event_type}")
        
        handlers = {
            "checkout.session.completed": handle_checkout_completed,
            "customer.subscription.created": handle_subscription_created,
            "customer.subscription.updated": handle_subscription_updated,
            "customer.subscription.deleted": handle_subscription_deleted,
            "invoice.payment_succeeded": handle_payment_succeeded,
            "invoice.payment_failed": handle_payment_failed,
            "invoice.paid": handle_payment_succeeded
        }
        
        handler = handlers.get(event_type)
        if handler:
            return handler(data)
        else:
            print(f"ℹ️ Unhandled event: {event_type}")
            return {"success": True, "message": f"Event {event_type} acknowledged"}
        
    except Exception as e:
        print(f"❌ Error handling webhook {event_type}: {e}")
        return {"success": False, "error": str(e)}

def handle_checkout_completed(session_data: Dict) -> Dict:
    """Maneja checkout completado"""
    try:
        user_id = session_data.get("metadata", {}).get("user_id")
        plan_id = session_data.get("metadata", {}).get("plan_id")
        subscription_id = session_data.get("subscription")
        customer_id = session_data.get("customer")
        
        if not user_id or not plan_id:
            return {"success": False, "error": "Missing metadata"}
        
        # Obtener detalles de Stripe
        stripe_subscription = stripe.Subscription.retrieve(subscription_id)
        
        now = datetime.now(timezone.utc)
        
        subscription_record = {
            "user_id": user_id,
            "plan_id": int(plan_id),
            "status": "active",
            "stripe_subscription_id": subscription_id,
            "stripe_customer_id": customer_id,
            "starts_at": now.isoformat(),
            "current_period_start": datetime.fromtimestamp(
                stripe_subscription.get('current_period_start', int(now.timestamp())),
                tz=timezone.utc
            ).isoformat() if stripe_subscription.get('current_period_start') else now.isoformat(),
            "current_period_end": datetime.fromtimestamp(
                stripe_subscription.get('current_period_end', int(now.timestamp()) + 30*24*60*60),
                tz=timezone.utc
            ).isoformat() if stripe_subscription.get('current_period_end') else (now + timedelta(days=30)).isoformat(),
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        
        # Cancelar suscripciones anteriores
        supabase.table("user_subscriptions").update({
            "status": "replaced",
            "canceled_at": now.isoformat()
        }).eq("user_id", user_id).eq("status", "active").execute()
        
        # Insertar nueva suscripción
        result = supabase.table("user_subscriptions").insert(subscription_record).execute()
        
        if result.data:
            print(f"✅ Subscription created for user {user_id}")
            return {"success": True, "message": "Subscription activated"}
        else:
            return {"success": False, "error": "Failed to create subscription"}
        
    except Exception as e:
        print(f"❌ Error in checkout completed: {e}")
        return {"success": False, "error": str(e)}

def handle_subscription_created(subscription_data: Dict) -> Dict:
    """Maneja creación de suscripción"""
    try:
        # Si ya se manejó en checkout, no hacer nada
        stripe_subscription_id = subscription_data.get("id")
        existing = (
            supabase.table("user_subscriptions")
            .select("id")
            .eq("stripe_subscription_id", stripe_subscription_id)
            .execute()
        )
        
        if existing.data:
            return {"success": True, "message": "Subscription already exists"}
        
        return {"success": True, "message": "Handled by checkout"}
        
    except Exception as e:
        print(f"❌ Error in subscription created: {e}")
        return {"success": False, "error": str(e)}

def handle_subscription_updated(subscription_data: Dict) -> Dict:
    """Maneja actualizaciones de suscripción"""
    try:
        stripe_subscription_id = subscription_data.get("id")
        status = subscription_data.get("status")
        
        # Mapear estados
        status_mapping = {
            "active": "active",
            "canceled": "canceled", 
            "past_due": "past_due",
            "unpaid": "past_due",
            "incomplete": "active",
            "incomplete_expired": "expired",
            "trialing": "active"
        }
        
        mapped_status = status_mapping.get(status, "active")
        
        update_data = {
            "status": mapped_status,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        if status == "canceled":
            update_data["canceled_at"] = datetime.now(timezone.utc).isoformat()
        
        supabase.table("user_subscriptions").update(update_data).eq(
            "stripe_subscription_id", stripe_subscription_id
        ).execute()
        
        print(f"✅ Subscription {stripe_subscription_id} updated to {mapped_status}")
        return {"success": True, "message": f"Updated to {mapped_status}"}
        
    except Exception as e:
        print(f"❌ Error updating subscription: {e}")
        return {"success": False, "error": str(e)}

def handle_subscription_deleted(subscription_data: Dict) -> Dict:
    """Maneja eliminación de suscripción"""
    try:
        stripe_subscription_id = subscription_data.get("id")
        
        supabase.table("user_subscriptions").update({
            "status": "canceled",
            "canceled_at": datetime.now(timezone.utc).isoformat(),
            "ends_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("stripe_subscription_id", stripe_subscription_id).execute()
        
        print(f"✅ Subscription {stripe_subscription_id} deleted")
        return {"success": True, "message": "Subscription deleted"}
        
    except Exception as e:
        print(f"❌ Error deleting subscription: {e}")
        return {"success": False, "error": str(e)}

def handle_payment_succeeded(invoice_data: Dict) -> Dict:
    """Maneja pagos exitosos"""
    try:
        subscription_id = invoice_data.get("subscription")
        
        if subscription_id:
            supabase.table("user_subscriptions").update({
                "status": "active",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("stripe_subscription_id", subscription_id).execute()
            
            print(f"✅ Payment succeeded for {subscription_id}")
        
        return {"success": True, "message": "Payment processed"}
        
    except Exception as e:
        print(f"❌ Error handling payment success: {e}")
        return {"success": False, "error": str(e)}
    

def get_available_plans() -> List[Dict]:
    """Obtiene todos los planes disponibles"""
    try:
        result = (
            supabase.table("subscription_plans")
            .select("*")
            .eq("is_active", True)
            .order("sort_order")
            .execute()
        )
        
        plans = []
        for plan in result.data:
            plans.append({
                "id": plan.get("id"),
                "name": plan.get("name"),
                "slug": plan.get("slug"),
                "price": plan.get("price"),
                "currency": plan.get("currency"),
                "billing_interval": plan.get("billing_interval"),
                "features": plan.get("features", []),
                "stripe_price_id": plan.get("stripe_price_id")
            })
        
        return plans
        
    except Exception as e:
        print(f"❌ Error getting available plans: {e}")
        return []

def handle_payment_failed(invoice_data: Dict) -> Dict:
    """Maneja fallos de pago"""
    try:
        subscription_id = invoice_data.get("subscription")
        
        if subscription_id:
            supabase.table("user_subscriptions").update({
                "status": "past_due",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("stripe_subscription_id", subscription_id).execute()
            
            print(f"⚠️ Payment failed for {subscription_id}")
        
        return {"success": True, "message": "Payment failure processed"}
        
    except Exception as e:
        print(f"❌ Error handling payment failure: {e}")
        return {"success": False, "error": str(e)}