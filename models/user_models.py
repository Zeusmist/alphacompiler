from typing import Optional
from pydantic import BaseModel
from datetime import datetime
from pydantic import BaseModel, EmailStr, validator, root_validator


class User(BaseModel):
    id: int
    email: Optional[str] = None
    wallet_address: Optional[str] = None
    role: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    subscription_end_date: Optional[datetime] = None
    crypto_customer_id: Optional[str] = None
    affiliate_code: Optional[str] = None
    referred_by_user_id: Optional[int] = None
    payout_option: Optional[str] = None


class UserSignup(BaseModel):
    email: Optional[EmailStr] = None
    wallet_address: Optional[str] = None
    affiliate_code: Optional[str] = None

    @root_validator(pre=True)
    def check_email_or_wallet(cls, values):
        email = values.get("email")
        wallet_address = values.get("wallet_address")
        if not email and not wallet_address:
            raise ValueError("Either email or wallet_address must be provided")
        return values


class Referral(BaseModel):
    id: int
    referrer_id: int
    referred_id: int
    created_at: datetime
