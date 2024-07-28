from typing import Optional
import asyncpg
import aiohttp
from datetime import datetime, timezone
from dateutil.parser import parse
from lib.config import pg_user, pg_password, pg_host, pg_database
import logging
import json
from aioredis import Redis

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


class Database:
    def __init__(self):
        self.pool = None
        self.redis = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(
            user=pg_user,
            password=pg_password,
            database=pg_database,
            host=pg_host,
        )
        async with self.pool.acquire() as conn:
            await conn.execute("SET timezone TO 'UTC';")

        # Initialize Redis connection
        self.redis = Redis(host="localhost", port=6379, db=0, encoding="utf-8")

        # Test Redis connection
        await self.redis.set("test_key", "test_value")
        value = await self.redis.get("test_key")
        print(f"Retrieved value from Redis: {value}")

        logger.info("Database connected and redis initialized")

    async def close(self):
        await self.pool.close()
        await self.redis.close()
        logger.info("Database connection closed")

    async def save_alpha_call(self, alpha_call):
        async with self.pool.acquire() as conn:
            date = parse(alpha_call["date"])
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
            else:
                date = date.astimezone(timezone.utc)

            naive_utc_date = date.replace(tzinfo=None)

            await conn.execute(
                """
                INSERT INTO alpha_calls (
                    token_ticker, token_address, token_name, token_image, network, 
                    additional_info, channel_name, message_url, date, long_term
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
                alpha_call["token_ticker"],
                alpha_call["token_address"],
                alpha_call.get("token_name"),
                alpha_call.get("token_image"),
                alpha_call["network"],
                alpha_call.get("additional_info"),
                alpha_call["channel_name"],
                alpha_call["message_url"],
                naive_utc_date,
                alpha_call.get("long_term", False),
            )

    async def get_trending_tokens(self, time_window, limit: int = 10):
        cache_key = f"trending_tokens:{time_window}:{limit}"

        if self.redis:
            try:
                cached_data = await self.redis.get(cache_key)
                if cached_data:
                    logger.info("Returning cached result")
                    return json.loads(cached_data)
            except Exception as e:
                logger.error(f"Cache error: {e}")

        async with self.pool.acquire() as conn:
            try:
                now = datetime.now(timezone.utc)
                naive_utc_date = now.replace(tzinfo=None)
                print(f"Naive UTC date: {naive_utc_date}")
                query = """
                    SELECT 
                        token_ticker, 
                        network, 
                        token_address,
                        MAX(token_name) as token_name,
                        MAX(token_image) as token_image,
                        COUNT(*) as mention_count,
                        MAX(date) as latest_date
                    FROM alpha_calls
                    WHERE date > $1
                    GROUP BY token_ticker, network, token_address
                    ORDER BY mention_count DESC, latest_date DESC
                    LIMIT $2
                """
                rows = await conn.fetch(query, naive_utc_date - time_window, limit)

                trending_tokens = []
                async with aiohttp.ClientSession() as session:
                    for row in rows:
                        token_data = dict(row)
                        # trending_tokens.append(dict(row))

                        # Fetch additional data from DexScreener
                        token_address = token_data["token_address"]
                        network = token_data["network"]
                        dex_url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"

                        try:
                            async with session.get(dex_url) as response:
                                if response.status == 200:
                                    dex_data = await response.json()
                                    if dex_data["pairs"] and len(dex_data["pairs"]) > 0:
                                        pair = dex_data["pairs"][0]

                                        token_data.update(
                                            {
                                                "pair": f"{pair['baseToken']['symbol']}/{pair['quoteToken']['symbol']}",
                                                "price": (
                                                    pair["priceUsd"]
                                                    if pair.get("priceUsd")
                                                    else 0
                                                ),
                                                "24h_change": pair["priceChange"][
                                                    "h24"
                                                ],
                                                "24h_volume": pair["volume"]["h24"],
                                            }
                                        )
                                    else:
                                        logger.warning(
                                            f"Failed to fetch data from DexScreener for {token_address}"
                                        )

                        except Exception as e:
                            logger.error(f"Error fetching DexScreener data: {e}")

                        trending_tokens.append(token_data)

                if self.redis:
                    try:
                        await self.redis.set(
                            cache_key,
                            json.dumps(trending_tokens, default=json_serial),
                            ex=60 * 5,
                        )
                    except Exception as e:
                        logger.error(f"Failed to set redis: {e}")

                return trending_tokens

            except Exception as e:
                logger.error(f"An error occurred: {e}")
                return None

    async def get_network_for_ticker(self, ticker):
        print(f"Fetching network for ticker: {ticker}")
        async with self.pool.acquire() as conn:
            try:
                result = await conn.fetchrow(
                    """
                    SELECT network, COUNT(*) as count
                    FROM alpha_calls
                    WHERE token_ticker = $1
                    GROUP BY network
                    ORDER BY count DESC
                    LIMIT 1
                    """,
                    ticker,
                )
                print(f"Network found: {result['network'] if result else None}")
                return result["network"] if result else None
            except Exception as e:
                print(f"An error occurred while fetching network for ticker: {e}")
                return None

    async def get_user_by_email(self, email: str):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM users WHERE email = $1", email)

    async def get_user_by_wallet(self, wallet_address: str):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(
                "SELECT * FROM users WHERE wallet_address = $1", wallet_address
            )

    async def create_user(
        self,
        email: Optional[str],
        hashed_password: Optional[str],
        wallet_address: Optional[str],
    ):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(
                """
                INSERT INTO users (email, hashed_password, wallet_address)
                VALUES ($1, $2, $3)
                RETURNING id, email, wallet_address
                """,
                email,
                hashed_password,
                wallet_address,
            )

    async def update_user_wallet(self, email: str, wallet_address: str):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(
                """
                UPDATE users
                SET wallet_address = $2
                WHERE email = $1
                RETURNING id, email, wallet_address
                """,
                email,
                wallet_address,
            )


db = Database()
