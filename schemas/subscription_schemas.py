from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class CheckoutRequest(BaseModel):
    plan_slug: str
    billing_interval: str = "monthly"

class TrialRequest(BaseModel):
    accept_terms: bool = True

class PlanResponse(BaseModel):
    id: int
    name: str
    slug: str
    price: float
    currency: str
    billing_interval: str
    features: List[str]
    stripe_price_id: str

class SubscriptionResponse(BaseModel):
    id: Optional[int]
    status: str
    plan: dict
    starts_at: Optional[str]
    ends_at: Optional[str]
    current_period_end: Optional[str]

class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str