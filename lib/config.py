import os
from dotenv import load_dotenv

load_dotenv()

allowed_origins = os.getenv("ALLOWED_ORIGINS").split(",")

frontend_url = os.getenv("FRONTEND_URL")

telegram_api_id = os.getenv("TELEGRAM_API_ID")
telegram_api_hash = os.getenv("TELEGRAM_API_HASH")
telegram_phone_number = os.getenv("TELEGRAM_PHONE_NUMBER")
telegram_channel_usernames = os.getenv("TELEGRAM_CHANNEL_USERNAMES").split(",")

google_ai_api_key = os.getenv("GOOGLE_AI_API_KEY")

pg_user = os.getenv("POSTGRES_USER")
pg_password = os.getenv("POSTGRES_PASSWORD")
pg_database = os.getenv("POSTGRES_DB")
pg_host = os.getenv("POSTGRES_HOST")

redis_host = os.getenv("REDIS_HOST")
redis_port = os.getenv("REDIS_PORT")
redis_db = os.getenv("REDIS_DB")

secret_key = os.getenv("SECRET_KEY")  # Change this to a secure random key

jwt_algorithm = "HS256"
access_token_expire_minutes = 2880  # 2 days

stripe_api_key = os.getenv("STRIPE_API_KEY")
stripe_webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

crypto_payment_address = os.getenv("CRYPTO_PAYMENT_ADDRESS")

# fees should be in cents
subscription_fees = {
    "monthly": os.getenv("MONTHLY_SUBSCRIPTION_FEE"),
    "yearly": os.getenv("YEARLY_SUBSCRIPTION_FEE"),
}
