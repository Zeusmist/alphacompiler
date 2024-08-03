from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from pydantic import BaseModel
from datetime import timedelta, datetime
from db.db_operations import db_operations
from user_operations import (
    get_user_by_email,
    get_user_by_wallet,
    create_user,
    create_access_token,
)
from lib.config import access_token_expire_minutes, stripe_webhook_secret
from helpers.api_helpers import (
    get_user_by_identifier,
    get_current_user,
    get_premium_user,
)
from models.user_models import User, UserSignup
from payments import create_stripe_customer, create_stripe_subscription
import stripe


app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenRequest(BaseModel):
    identifier: str  # This can be either email or wallet address


class SubscriptionRequest(BaseModel):
    plan: str
    payment_method: str
    payment_details: dict


@app.on_event("startup")
async def startup():
    await db_operations.connect()


@app.on_event("shutdown")
async def shutdown():
    await db_operations.close()


@app.post("/token", response_model=Token)
async def login_for_access_token(token_request: TokenRequest):
    user = await get_user_by_identifier(token_request.identifier)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.email or user.wallet_address},
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/signup")
async def signup(user: UserSignup):
    if user.email:
        existing_user = await get_user_by_email(user.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
    elif user.wallet_address:
        existing_wallet = await get_user_by_wallet(user.wallet_address)
        if existing_wallet:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Wallet address already registered",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either email or wallet address must be provided",
        )

    new_user = await create_user(user.email, user.wallet_address)
    return {"message": "User created successfully", "user_id": new_user.id}


@app.post("/connect_wallet")
async def connect_wallet(
    wallet_address: str, current_user: User = Depends(get_current_user)
):
    existing_wallet = await get_user_by_wallet(wallet_address)
    if existing_wallet:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Wallet address already registered",
        )
    updated_user = await db_operations.user_repo.update_user_wallet(
        current_user.email, wallet_address
    )
    return {"message": "Wallet connected successfully", "user": updated_user}


@app.post("/connect_email")
async def connect_email(email: str, current_user: User = Depends(get_current_user)):
    existing_user = await get_user_by_email(email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    updated_user = await db_operations.user_repo.update_user_email(
        current_user.email, email
    )
    return {"message": "Email connected successfully", "user": updated_user}


@app.get("/trending_tokens")
async def get_trending_tokens(
    time_window: str = "24h",
    current_user: Optional[User] = Depends(get_current_user),
    limit: int = 10,
):
    limit = limit if current_user and current_user.role == "premium" else 3
    # Convert time_window to timedelta
    if time_window == "24h":
        window = timedelta(hours=24)
    elif time_window == "7d":
        window = timedelta(days=7)
    else:
        window = timedelta(days=3)  # Default to 3 days

    trending_tokens = await db_operations.token_repo.get_trending_tokens(
        window, limit=limit
    )
    return {"trending_tokens": trending_tokens}


@app.post("/create-subscription")
async def create_subscription(
    price_id,
    current_user: User = Depends(get_current_user),
):
    try:
        customer_id = await create_stripe_customer(current_user.email)

        subscription = await create_stripe_subscription(
            customer_id=customer_id, price_id=price_id
        )

        await db_operations.user_repo.update_user_role(
            current_user.id,
            "premium",
            stripe_customer_id=customer_id,
            stripe_subscription_id=subscription.id,
            subscription_end_date=datetime.fromtimestamp(
                subscription.current_period_end
            ),
        )

        return {
            "subscription_id": subscription.id,
            "client_secret": subscription.latest_invoice.payment_intent.client_secret,
        }
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/cancel-subscription")
async def cancel_subscription(current_user: User = Depends(get_premium_user)):
    try:
        # Retrieve the user's Stripe subscription ID
        user = await db_operations.user_repo.get_user_by_id(current_user.id)
        if not user.stripe_subscription_id:
            raise HTTPException(status_code=400, detail="No active subscription found")

        # Cancel the subscription at the end of the current period
        stripe.Subscription.modify(
            user.stripe_subscription_id, cancel_at_period_end=True
        )

        # Update user role in the database
        await db_operations.user_repo.update_user_role(
            current_user.id,
            "basic",
            subscription_end_date=datetime.fromtimestamp(user.subscription_end_date),
        )

        return {"message": "Subscription cancelled successfully"}
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, stripe_webhook_secret
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] == "invoice.payment_succeeded":
        subscription_id = event["data"]["object"]["subscription"]
        # Update the user's subscription end date
        await db_operations.user_repo.update_subscription_end_date(
            subscription_id,
            datetime.fromtimestamp(
                event["data"]["object"]["lines"]["data"][0]["period"]["end"]
            ),
        )
    elif event["type"] == "customer.subscription.deleted":
        subscription_id = event["data"]["object"]["id"]
        # Update the user's role to basic
        await db_operations.user_repo.update_user_role_by_subscription(
            subscription_id, "basic"
        )

    return {"status": "success"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
