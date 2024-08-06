from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import timedelta, datetime
from db.db_operations import db_operations
from user_operations import (
    get_user_by_email,
    get_user_by_wallet,
    create_user,
    create_access_token,
)
from lib.config import (
    access_token_expire_minutes,
    stripe_webhook_secret,
    allowed_origins,
    monthly_subscription_fee,
    yearly_subscription_fee,
    crypto_payment_address,
)
from helpers.api_helpers import (
    get_user_by_identifier,
    get_current_user,
    get_premium_user,
)
from models.user_models import User, UserSignup
from payments import (
    create_stripe_customer,
    create_stripe_subscription,
    create_checkout_session,
    process_crypto_subscription,
)
import stripe


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


def get_access_token(identifier: str):
    return create_access_token(
        data={"sub": identifier},
        expires_delta=timedelta(minutes=access_token_expire_minutes),
    )


class TokenUser(BaseModel):
    access_token: str
    user: User


class TokenRequest(BaseModel):
    identifier: str  # This can be either email or wallet address


class SubscriptionRequest(BaseModel):
    price_id: str


class UpdateUser(BaseModel):
    email: Optional[str] = None
    wallet_address: Optional[str] = None


class CryptoSubscriptionRequest(BaseModel):
    plan: str


class VerifyCryptoPaymentRequest(BaseModel):
    tx_hash: str
    token: str
    plan: str
    sender_address: str


@app.on_event("startup")
async def startup():
    await db_operations.connect()


@app.on_event("shutdown")
async def shutdown():
    await db_operations.close()


@app.post("/token", response_model=TokenUser)
async def login_for_access_token(token_request: TokenRequest):
    user = await get_user_by_identifier(token_request.identifier)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found. Please sign up",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = get_access_token(user.email or user.wallet_address)
    return {
        "access_token": access_token,
        "user": user,
    }


@app.post("/signup", response_model=TokenUser)
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

    access_token = get_access_token(user.email or user.wallet_address)

    return {
        "access_token": access_token,
        "user": new_user,
    }


@app.get("/login", response_model=TokenUser)
async def connect_wallet(current_user: User = Depends(get_current_user)):
    access_token = get_access_token(current_user.email or current_user.wallet_address)
    return {
        "access_token": access_token,
        "user": current_user,
    }


@app.post("/connect_wallet")
async def connect_wallet(
    request: UpdateUser, current_user: User = Depends(get_current_user)
):
    existing_wallet = await get_user_by_wallet(request.wallet_address)
    if existing_wallet:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Wallet address already registered",
        )
    await db_operations.user_repo.update_user_wallet(
        current_user.id, request.wallet_address
    )
    return {"wallet_address": request.wallet_address}


@app.post("/connect_email")
async def connect_email(
    request: UpdateUser, current_user: User = Depends(get_current_user)
):
    existing_user = await get_user_by_email(request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    await db_operations.user_repo.update_user_email(current_user.id, request.email)
    return {"email": request.email}


@app.get("/trending_tokens")
async def get_trending_tokens(
    time_window: str = "24h",
    current_user: Optional[User] = Depends(get_current_user),
    limit: int = 10,
    sort_by: str = "mention_count",
    sort_order: str = "desc",
):
    limit = limit if current_user and current_user.role == "premium" else 3

    # if time window ends with h, use hours, if time window ends with d, use days
    if time_window[-1] == "h":
        window = timedelta(hours=int(time_window[:-1]))
    elif time_window[-1] == "d":
        window = timedelta(days=int(time_window[:-1]))
    else:
        window = timedelta(days=3)

    window = (
        window if current_user and current_user.role == "premium" else timedelta(days=7)
    )

    # # Convert time_window to timedelta
    # if time_window == "24h":
    #     window = timedelta(hours=24)
    # elif time_window == "7d":
    #     window = timedelta(days=7)
    # else:
    #     window = timedelta(days=3)  # Default to 3 days

    try:
        trending_tokens = await db_operations.token_repo.get_trending_tokens(
            window,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        return {"trending_tokens": trending_tokens}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/create-subscription")
async def create_subscription(
    request: SubscriptionRequest,
    current_user: User = Depends(get_current_user),
):
    print(
        f"Creating subscription for user: {request.price_id} - {current_user.email or current_user.wallet_address}"
    )
    try:
        if current_user.stripe_customer_id:
            customer_id = current_user.stripe_customer_id
        else:
            customer_id = await create_stripe_customer(
                current_user.email or current_user.wallet_address
            )
            if not customer_id:
                raise HTTPException(status_code=400, detail="Failed to create customer")

        if current_user.stripe_subscription_id:
            # create a payment link
            payment_link = await create_checkout_session(request.price_id, customer_id)

            if not payment_link:
                raise HTTPException(
                    status_code=400,
                    detail="Failed to create payment link. Please try again.",
                )

            return {"payment_link": payment_link}
        else:
            subscription = await create_stripe_subscription(
                customer_id=customer_id,
                price_id=request.price_id,
            )

            if not subscription:
                raise HTTPException(
                    status_code=400,
                    detail="Failed to create subscription. Please try again.",
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

            return {"subscription_id": subscription.id, "trial_period_days": 3}

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


@app.post("/create-crypto-subscription")
async def create_crypto_subscription(
    request: CryptoSubscriptionRequest,
    current_user: User = Depends(get_current_user),
):
    if not current_user.wallet_address:
        raise HTTPException(status_code=400, detail="Please connect your wallet first")

    print(
        f"Creating crypto subscription for user: {request.plan} - {current_user.wallet_address}"
    )

    try:
        if not current_user.crypto_customer_id:
            # update user role to premium because of 3 day free trial
            await db_operations.user_repo.crypto_update_user_role(
                current_user.id,
                "premium",
                crypto_customer_id=current_user.wallet_address,
                subscription_end_date=datetime.fromtimestamp(
                    datetime.now().timestamp() + 3 * 24 * 60 * 60
                ),
            )

            return {
                "crypto_customer_id": current_user.wallet_address,
                "trial_period_days": 3,
            }
        else:
            # send payment details
            price_mapping = {
                "monthly": monthly_subscription_fee,
                "yearly": yearly_subscription_fee,
            }
            amount = price_mapping.get(request.plan)
            if not amount:
                raise HTTPException(status_code=400, detail="Invalid subscription plan")

            return {"amount": amount, "payment_address": crypto_payment_address}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/verify-crypto-payment")
async def verify_crypto_payment(
    request: VerifyCryptoPaymentRequest,
    current_user: User = Depends(get_current_user),
):
    subscriptionInfo = await process_crypto_subscription(
        user_id=current_user.id,
        token=request.token,
        tx_hash=request.tx_hash,
        plan=request.plan,
        sender_address=request.sender_address,
    )

    if not subscriptionInfo:
        raise HTTPException(status_code=400, detail="Payment verification failed")

    await db_operations.user_repo.crypto_update_user_role(
        current_user.id,
        "premium",
        crypto_customer_id=current_user.wallet_address,
        subscription_end_date=datetime.fromtimestamp(
            subscriptionInfo["subscription_end_date"]
        ),
    )

    return {"subscription_end_date": subscriptionInfo["subscription_end_date"]}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
