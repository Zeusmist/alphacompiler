import stripe
from web3 import Web3
from web3.middleware import geth_poa_middleware
from lib.config import stripe_api_key, crypto_payment_address
from typing import Dict, Any, Optional
from lib.config import (
    frontend_url,
    ethereum_node_url,
    monthly_subscription_fee,
    yearly_subscription_fee,
)
from datetime import datetime, timedelta

stripe.api_key = stripe_api_key

# Initialize Web3 connection (replace with your Ethereum node URL)
w3 = Web3(Web3.HTTPProvider(ethereum_node_url))
if w3.is_connected():
    print("Successfully connected to Ethereum network via Alchemy")
else:
    print("Failed to connect to Ethereum network")

w3.middleware_onion.inject(geth_poa_middleware, layer=0)

# USDC and USDT contract addresses on Ethereum mainnet
USDC_ADDRESS = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
USDT_ADDRESS = "0xdAC17F958D2ee523a2206206994597C13D831ec7"

# Contract ABI for USDC and USDT (only including necessary functions)
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"},
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
]


async def verify_crypto_payment(
    tx_hash: str, plan: str, token: str, sender_address: str
) -> bool:
    token_address = USDC_ADDRESS if token == "USDC" else USDT_ADDRESS
    token_contract = w3.eth.contract(address=token_address, abi=ERC20_ABI)

    try:
        # Get transaction details
        tx = w3.eth.get_transaction(tx_hash)
        tx_receipt = w3.eth.get_transaction_receipt(tx_hash)

        # Check if transaction is confirmed
        if tx_receipt["status"] != 1:
            print(f"Transaction failed: {tx_hash}")
            return False

        # Verify sender address
        if tx["from"] != sender_address:
            print(
                f"Sender address mismatch: expected {sender_address}, got {tx['from']}"
            )
            return False

        # Decode the transaction input
        decoded_input = token_contract.decode_function_input(tx["input"])

        if (
            decoded_input[0].fn_name != "transfer"
            or decoded_input[1]["_to"] != crypto_payment_address
        ):
            print(f"Invalid transaction: not a transfer to the expected address")
            return False

        # Get the number of decimals for the token
        decimals = token_contract.functions.decimals().call()

        price_mapping = {
            "monthly": monthly_subscription_fee,
            "yearly": yearly_subscription_fee,
        }
        expected_amount = price_mapping.get(plan)

        # Convert the expected amount to token units
        expected_amount_in_token = expected_amount * (10**decimals)

        # Verify the amount
        if decoded_input[1]["_value"] != expected_amount_in_token:
            print(
                f"Amount mismatch: expected {expected_amount_in_token}, got {decoded_input[1]['_value']}"
            )
            return False

        print(f"Payment verified: TX Hash {tx_hash}")
        return True

    except Exception as e:
        print(f"Error verifying transaction: {str(e)}")
        return False


async def process_crypto_subscription(
    plan: str, token: str, tx_hash: str, sender_address: str
) -> bool:
    # Verify the payment and update the user's subscription
    payment_confirmed = await verify_crypto_payment(
        tx_hash=tx_hash,
        plan=plan,
        token=token,
        sender_address=sender_address,
    )

    if payment_confirmed:
        days = 365 if plan == "yearly" else 30
        subscription_end_date = datetime.timestamp(
            datetime.now() + timedelta(days=days)
        )
        return {"subscription_end_date": subscription_end_date}
    return None


async def create_stripe_customer(email: str) -> str:
    try:
        customer = stripe.Customer.create(name=email)
        return customer.id
    except stripe.error.StripeError as e:
        print(f"Stripe error creating customer: {str(e)}")
        return None


async def create_checkout_session(price_id: str, customer_id: str) -> Optional[str]:
    try:
        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=f"{frontend_url}/dashboard?success=true",
            cancel_url=f"{frontend_url}/dashboard?canceled=true",
        )
        return checkout_session.url
    except stripe.error.StripeError as e:
        print(f"Stripe error creating checkout session: {str(e)}")
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
