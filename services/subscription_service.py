# services/subscription_service.py - CORREGIDO
import os
import stripe
from datetime import datetime, timezone
from uuid import UUID
from supabase import create_client, Client
from dotenv import load_dotenv
from typing import Dict, Optional

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:4200")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def create_checkout_session(user_id: UUID, plan_slug: str, billing_interval: str = "monthly") -> Dict:
    """Crea una sesión de checkout de Stripe"""
    try:
        # Obtener el plan
        plan_result = (
            supabase.table("subscription_plans")
            .select("*")
            .eq("slug", plan_slug)
            .eq("billing_interval", billing_interval)
            .eq("is_active", True)
            .single()
            .execute()
        )
        
        if not plan_result.data:
            return {"success": False, "error": "Plan not found"}
        
        plan = plan_result.data
        stripe_price_id = plan.get("stripe_price_id")
        
        if not stripe_price_id:
            return {"success": False, "error": "Stripe price ID not configured for this plan"}
        
        # Obtener información del usuario
        user_id_str = str(user_id)
        auth_user = supabase.auth.admin.get_user_by_id(user_id_str)
        
        if not auth_user.user:
            return {"success": False, "error": "User not found"}
        
        # Crear o obtener customer de Stripe
        customer_email = auth_user.user.email
        stripe_customer_id = get_or_create_stripe_customer(user_id_str, customer_email)
        
        # Crear sesión de checkout
        session = stripe.checkout.Session.create(
            customer=stripe_customer_id,
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{
                "price": stripe_price_id,
                "quantity": 1,
            }],
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
        
        print(f"✅ Checkout session creada: {session.id} para usuario {user_id_str}")
        
        return {
            "success": True,
            "checkout_url": session.url,
            "session_id": session.id
        }
        
    except stripe.error.StripeError as e:
        print(f"❌ Stripe error: {e}")
        return {"success": False, "error": f"Payment error: {str(e)}"}
    except Exception as e:
        print(f"❌ Error creating checkout session: {e}")
        return {"success": False, "error": str(e)}

def get_or_create_stripe_customer(user_id: str, email: str) -> str:
    """Obtiene o crea un customer de Stripe"""
    try:
        # Verificar si ya existe un customer
        existing_sub = (
            supabase.table("user_subscriptions")
            .select("stripe_customer_id")
            .eq("user_id", user_id)
            .not_.is_("stripe_customer_id", "null")
            .limit(1)
            .execute()
        )
        
        if existing_sub.data and existing_sub.data[0].get("stripe_customer_id"):
            customer_id = existing_sub.data[0]["stripe_customer_id"]
            print(f"✅ Customer existente encontrado: {customer_id}")
            return customer_id
        
        # Crear nuevo customer
        customer = stripe.Customer.create(
            email=email,
            metadata={"user_id": user_id}
        )
        
        print(f"✅ Nuevo customer creado: {customer.id}")
        return customer.id
        
    except Exception as e:
        print(f"❌ Error creating Stripe customer: {e}")
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
            
            print(f"✅ Suscripción cancelada: {stripe_subscription_id}")
            
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
        print(f"❌ Stripe error canceling subscription: {e}")
        return {"success": False, "error": f"Payment error: {str(e)}"}
    except Exception as e:
        print(f"❌ Error canceling subscription: {e}")
        return {"success": False, "error": str(e)}

def handle_stripe_webhook(event_type: str, data: Dict) -> Dict:
    """Maneja los webhooks de Stripe"""
    try:
        print(f"🔄 Procesando webhook: {event_type}")
        
        if event_type == "checkout.session.completed":
            return handle_checkout_completed(data)
        elif event_type == "customer.subscription.created":
            return handle_subscription_created(data)
        elif event_type == "customer.subscription.updated":
            return handle_subscription_updated(data)
        elif event_type == "customer.subscription.deleted":
            return handle_subscription_deleted(data)
        elif event_type == "invoice.payment_succeeded":
            return handle_payment_succeeded(data)
        elif event_type == "invoice.payment_failed":
            return handle_payment_failed(data)
        else:
            print(f"ℹ️ Evento no manejado: {event_type}")
            return {"success": True, "message": f"Event {event_type} acknowledged but not processed"}
        
    except Exception as e:
        print(f"❌ Error handling webhook {event_type}: {e}")
        return {"success": False, "error": str(e)}

def handle_checkout_completed(session_data: Dict) -> Dict:
    """Maneja el evento de checkout completado"""
    try:
        user_id = session_data.get("metadata", {}).get("user_id")
        plan_id = session_data.get("metadata", {}).get("plan_id")
        subscription_id = session_data.get("subscription")
        customer_id = session_data.get("customer")
        
        if not user_id or not plan_id:
            return {"success": False, "error": "Missing user_id or plan_id in metadata"}
        
        # Obtener detalles de la suscripción de Stripe
        stripe_subscription = stripe.Subscription.retrieve(subscription_id)
        
        # Crear registro de suscripción
        subscription_record = {
            "user_id": user_id,
            "plan_id": int(plan_id),
            "status": "active",
            "stripe_subscription_id": subscription_id,
            "stripe_customer_id": customer_id,
            "starts_at": datetime.fromtimestamp(
                stripe_subscription.current_period_start, 
                tz=timezone.utc
            ).isoformat(),
            "current_period_start": datetime.fromtimestamp(
                stripe_subscription.current_period_start, 
                tz=timezone.utc
            ).isoformat(),
            "current_period_end": datetime.fromtimestamp(
                stripe_subscription.current_period_end, 
                tz=timezone.utc
            ).isoformat()
        }
        
        # Cancelar cualquier suscripción activa anterior
        supabase.table("user_subscriptions").update({
            "status": "replaced",
            "canceled_at": datetime.now(timezone.utc).isoformat()
        }).eq("user_id", user_id).eq("status", "active").execute()
        
        # Insertar nueva suscripción
        result = supabase.table("user_subscriptions").insert(subscription_record).execute()
        
        if result.data:
            print(f"✅ Subscription created for user {user_id}")
            return {"success": True, "message": "Subscription activated"}
        else:
            return {"success": False, "error": "Failed to create subscription record"}
        
    except Exception as e:
        print(f"❌ Error handling checkout completed: {e}")
        return {"success": False, "error": str(e)}

def handle_subscription_created(subscription_data: Dict) -> Dict:
    """Maneja la creación de suscripción (evento separado de checkout)"""
    try:
        user_id = subscription_data.get("metadata", {}).get("user_id")
        
        if not user_id:
            return {"success": True, "message": "No user_id in subscription metadata"}
        
        # Si ya se manejó en checkout.session.completed, no hacer nada
        existing = (
            supabase.table("user_subscriptions")
            .select("id")
            .eq("stripe_subscription_id", subscription_data.get("id"))
            .execute()
        )
        
        if existing.data:
            return {"success": True, "message": "Subscription already exists"}
        
        return {"success": True, "message": "Subscription creation handled by checkout"}
        
    except Exception as e:
        print(f"❌ Error handling subscription created: {e}")
        return {"success": False, "error": str(e)}

def handle_subscription_updated(subscription_data: Dict) -> Dict:
    """Maneja actualizaciones de suscripción"""
    try:
        stripe_subscription_id = subscription_data.get("id")
        status = subscription_data.get("status")
        
        # Mapear estados de Stripe a nuestros estados
        status_mapping = {
            "active": "active",
            "canceled": "canceled",
            "past_due": "past_due",
            "unpaid": "past_due",
            "incomplete": "active",  # Tratar como activo temporalmente
            "incomplete_expired": "expired",
            "trialing": "active"
        }
        
        mapped_status = status_mapping.get(status, "active")
        
        # Actualizar en base de datos
        update_data = {
            "status": mapped_status,
            "current_period_start": datetime.fromtimestamp(
                subscription_data.get("current_period_start"), 
                tz=timezone.utc
            ).isoformat(),
            "current_period_end": datetime.fromtimestamp(
                subscription_data.get("current_period_end"), 
                tz=timezone.utc
            ).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        if status == "canceled":
            update_data["canceled_at"] = datetime.now(timezone.utc).isoformat()
            update_data["ends_at"] = datetime.fromtimestamp(
                subscription_data.get("current_period_end"), 
                tz=timezone.utc
            ).isoformat()
        
        result = supabase.table("user_subscriptions").update(update_data).eq(
            "stripe_subscription_id", stripe_subscription_id
        ).execute()
        
        print(f"✅ Subscription {stripe_subscription_id} updated to {mapped_status}")
        return {"success": True, "message": f"Subscription updated to {mapped_status}"}
        
    except Exception as e:
        print(f"❌ Error handling subscription updated: {e}")
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
        print(f"❌ Error handling subscription deleted: {e}")
        return {"success": False, "error": str(e)}

def handle_payment_succeeded(invoice_data: Dict) -> Dict:
    """Maneja pagos exitosos"""
    try:
        subscription_id = invoice_data.get("subscription")
        
        if subscription_id:
            # Asegurar que la suscripción esté activa
            supabase.table("user_subscriptions").update({
                "status": "active",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("stripe_subscription_id", subscription_id).execute()
            
            print(f"✅ Payment succeeded for subscription {subscription_id}")
        
        return {"success": True, "message": "Payment processed successfully"}
        
    except Exception as e:
        print(f"❌ Error handling payment succeeded: {e}")
        return {"success": False, "error": str(e)}

def handle_payment_failed(invoice_data: Dict) -> Dict:
    """Maneja fallos de pago"""
    try:
        subscription_id = invoice_data.get("subscription")
        
        if subscription_id:
            # Marcar como past_due
            supabase.table("user_subscriptions").update({
                "status": "past_due",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("stripe_subscription_id", subscription_id).execute()
            
            print(f"⚠️ Payment failed for subscription {subscription_id}")
        
        return {"success": True, "message": "Payment failure processed"}
        
    except Exception as e:
        print(f"❌ Error handling payment failed: {e}")
        return {"success": False, "error": str(e)}

# ========== UTILIDADES ==========

def get_user_plan_access(user_id: UUID) -> Dict:
    """Obtiene el acceso del usuario basado en su plan"""
    try:
        from services.user_service import get_current_subscription
        
        subscription = get_current_subscription(user_id)
        
        if not subscription:
            # Usuario sin suscripción - acceso básico
            return {
                "plan_slug": "basic",
                "has_premium": False,
                "max_conversations_per_day": 5,
                "max_words_per_day": 50,
                "priority_support": False,
                "status": "basic"
            }
        
        plan = subscription.get("plan", {})
        status = subscription.get("status", "active")
        
        # Si está en trial o activo, dar acceso completo
        has_premium = status in ["active", "trial"] and plan.get("slug") != "basic"
        
        return {
            "plan_slug": plan.get("slug", "basic"),
            "has_premium": has_premium,
            "max_conversations_per_day": plan.get("max_conversations", 5),
            "max_words_per_day": plan.get("max_words_per_day", 50),
            "priority_support": plan.get("priority_support", False),
            "status": status
        }
        
    except Exception as e:
        print(f"❌ Error getting user plan access: {e}")
        return {
            "plan_slug": "basic",
            "has_premium": False,
            "max_conversations_per_day": 5,
            "max_words_per_day": 50,
            "priority_support": False,
            "status": "error"
        }

def sync_subscription_from_stripe(stripe_subscription_id: str) -> Dict:
    """Sincroniza una suscripción desde Stripe (útil para debug)"""
    try:
        # Obtener suscripción de Stripe
        stripe_subscription = stripe.Subscription.retrieve(stripe_subscription_id)
        
        # Buscar en nuestra BD
        existing = (
            supabase.table("user_subscriptions")
            .select("*")
            .eq("stripe_subscription_id", stripe_subscription_id)
            .single()
            .execute()
        )
        
        if not existing.data:
            return {"success": False, "error": "Subscription not found in database"}
        
        # Actualizar con datos de Stripe
        update_data = {
            "status": stripe_subscription.status,
            "current_period_start": datetime.fromtimestamp(
                stripe_subscription.current_period_start, 
                tz=timezone.utc
            ).isoformat(),
            "current_period_end": datetime.fromtimestamp(
                stripe_subscription.current_period_end, 
                tz=timezone.utc
            ).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        supabase.table("user_subscriptions").update(update_data).eq(
            "stripe_subscription_id", stripe_subscription_id
        ).execute()
        
        return {"success": True, "message": "Subscription synced from Stripe"}
        
    except Exception as e:
        print(f"❌ Error syncing subscription: {e}")
        return {"success": False, "error": str(e)}

def get_subscription_analytics() -> Dict:
    """Obtiene analytics básicos de suscripciones (para admin)"""
    try:
        # Contar suscripciones por estado
        result = supabase.table("user_subscriptions").select("status").execute()
        
        status_counts = {}
        for sub in result.data:
            status = sub.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Contar usuarios con trial activo
        trial_result = supabase.table("users_profile").select("trial_start").not_.is_("trial_start", "null").execute()
        
        total_trials = len(trial_result.data) if trial_result.data else 0
        
        return {
            "success": True,
            "analytics": {
                "subscription_counts": status_counts,
                "total_trials": total_trials,
                "total_subscriptions": len(result.data) if result.data else 0
            }
        }
        
    except Exception as e:
        print(f"❌ Error getting analytics: {e}")
        return {"success": False, "error": str(e)}