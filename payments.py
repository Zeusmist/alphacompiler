import stripe
from web3 import Web3
from eth_account.messages import encode_defunct
from lib.config import stripe_api_key, crypto_payment_address, subscription_fees
from typing import Dict, Any
from decimal import Decimal

stripe.api_key = stripe_api_key

# Set up Web3 connection (you might want to move this to a separate file)
w3 = Web3(Web3.HTTPProvider("https://mainnet.infura.io/v3/YOUR-PROJECT-ID"))

# USDC and USDT contract addresses on Ethereum mainnet
USDC_CONTRACT = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
USDT_CONTRACT = "0xdAC17F958D2ee523a2206206994597C13D831ec7"

# ABI for ERC20 token transfer event
ERC20_TRANSFER_ABI = {
    "anonymous": False,
    "inputs": [
        {"indexed": True, "name": "from", "type": "address"},
        {"indexed": True, "name": "to", "type": "address"},
        {"indexed": False, "name": "value", "type": "uint256"},
    ],
    "name": "Transfer",
    "type": "event",
}


async def create_stripe_customer(email: str) -> str:
    try:
        customer = stripe.Customer.create(email=email)
        return customer.id
    except stripe.error.StripeError as e:
        print(f"Stripe error creating customer: {str(e)}")
        return None


async def create_stripe_subscription(customer_id: str, price_id: str) -> Dict[str, Any]:
    try:
        subscription = stripe.Subscription.create(
            customer=customer_id,
            items=[{"price": price_id}],
            trial_period_days=3,
            expand=["latest_invoice.payment_intent"],
        )
        return subscription
    except stripe.error.StripeError as e:
        print(f"Stripe error creating subscription: {str(e)}")
        return None


async def check_stripe_subscription(subscription_id: str) -> bool:
    try:
        subscription = stripe.Subscription.retrieve(subscription_id)
        if subscription.status == "active":
            # return the subscription interval (month or year) and current_period_end
            return {
                "interval": subscription.items.data[0].price.recurring.interval,
                "current_period_end": subscription.current_period_end,
            }

        return False
    except stripe.error.StripeError as e:
        print(f"Stripe error checking subscription: {str(e)}")
        return False


async def cancel_stripe_subscription(subscription_id: str) -> bool:
    try:
        canceled_subscription = stripe.Subscription.delete(subscription_id)
        return canceled_subscription.status == "canceled"
    except stripe.error.StripeError as e:
        print(f"Stripe error canceling subscription: {str(e)}")
        return False
