from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime
from db.db_operations import db_operations
from lib.config import (
    stripe_webhook_secret,
    monthly_subscription_fee,
    yearly_subscription_fee,
    crypto_payment_address,
)
from helpers.api_helpers import get_current_user, get_premium_user
from models.user_models import User
from payments import (
    create_stripe_customer,
    create_stripe_subscription,
    create_checkout_session,
    process_crypto_subscription,
)
from user_operations import create_commission
import stripe


router = APIRouter()


class SubscriptionRequest(BaseModel):
    price_id: str


class CryptoSubscriptionRequest(BaseModel):
    plan: str


class VerifyCryptoPaymentRequest(BaseModel):
    tx_hash: str
    token: str
    plan: str
    sender_address: str


@router.post("/create-subscription")
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


@router.post("/cancel-subscription")
async def cancel_subscription(current_user: User = Depends(get_premium_user)):
    try:
        # Retrieve the user's Stripe subscription ID
        user = await db_operations.user_repo.get_user_by_id(current_user.id)
        if user.role != "premium":
            raise HTTPException(status_code=400, detail="No active subscription found")

        if user.stripe_subscription_id:
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


async def process_stripe_webhook_event(event):
    if event["type"] == "invoice.payment_succeeded":
        subscription_id = event["data"]["object"]["subscription"]
        customer_id = event["data"]["object"]["customer"]
        amount_paid = (
            event["data"]["object"]["amount_paid"] / 100
        )  # Convert cents to dollars

        # Update the user's subscription end date
        user = await db_operations.user_repo.update_subscription_end_date(
            subscription_id,
            datetime.fromtimestamp(
                event["data"]["object"]["lines"]["data"][0]["period"]["end"]
            ),
        )

        if user and user["referred_by_user_id"]:
            # Create a commission for the referrer
            await create_commission(
                user["referred_by_user_id"], user["id"], amount_paid
            )

    elif event["type"] == "customer.subscription.deleted":
        subscription_id = event["data"]["object"]["id"]
        # Update the user's role to basic
        await db_operations.user_repo.update_user_role_by_subscription(
            subscription_id, "basic"
        )


@router.post("/webhook")
async def stripe_webhook(request: Request, background_tasks: BackgroundTasks):
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

    background_tasks.add_task(process_stripe_webhook_event, event)

    return {"status": "success"}


@router.post("/create-crypto-subscription")
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


@router.post("/verify-crypto-payment")
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

    if current_user.referred_by_user_id:
        # Create a commission for the referrer
        await create_commission(
            current_user.referred_by_user_id,
            current_user.id,
            subscriptionInfo["amount"],
        )

    return {"subscription_end_date": subscriptionInfo["subscription_end_date"]}
