import os
from dotenv import load_dotenv

load_dotenv()

telegram_api_id = os.getenv("TELEGRAM_API_ID")
telegram_api_hash = os.getenv("TELEGRAM_API_HASH")
telegram_phone_number = os.getenv("TELEGRAM_PHONE_NUMBER")
telegram_channel_usernames = os.getenv("TELEGRAM_CHANNEL_USERNAMES").split(",")

google_ai_api_key = os.getenv("GOOGLE_AI_API_KEY")

pg_user = os.getenv("POSTGRES_USER")
pg_password = os.getenv("POSTGRES_PASSWORD")
pg_database = os.getenv("POSTGRES_DB")
pg_host = os.getenv("POSTGRES_HOST")
