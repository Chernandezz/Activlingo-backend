import os
import stripe
from dotenv import load_dotenv

load_dotenv()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
PRICE_ID = os.getenv("STRIPE_PRICE_ID")

def create_checkout_session(user_id: str):
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{
                "price": PRICE_ID,
                "quantity": 1,
            }],
            customer_email=None,
            metadata={"user_id": user_id},
            success_url="https://tuapp.com/success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="https://tuapp.com/cancel",
        )
        return session.url
    except Exception as e:
        raise Exception(f"Stripe error: {str(e)}")
