import asyncpg
from datetime import datetime, timezone
from dateutil.parser import parse
from lib.config import pg_user, pg_password, pg_host, pg_database


class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(
            user=pg_user,
            password=pg_password,
            database=pg_database,
            host=pg_host,
        )
        async with self.pool.acquire() as conn:
            await conn.execute("SET timezone TO 'UTC';")

    async def close(self):
        await self.pool.close()

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
                    token_ticker, token_address, network, confidence, 
                    additional_info, channel_name, message_url, date, long_term
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
                alpha_call["token_ticker"],
                alpha_call["token_address"],
                alpha_call["network"],
                alpha_call["confidence"],
                alpha_call["additional_info"],
                alpha_call["channel_name"],
                alpha_call["message_url"],
                naive_utc_date,
                alpha_call["long_term"],
            )

    async def get_trending_tokens(self, time_window):
        async with self.pool.acquire() as conn:
            now = datetime.now(timezone.utc)
            naive_utc_date = now.replace(tzinfo=None)
            # use a try catch to get the trending tokens
            try:
                trending_tokens = await conn.fetch(
                    """
                    SELECT token_ticker, network, COUNT(*) as mention_count, 
                          AVG(confidence) as avg_confidence
                    FROM alpha_calls
                    WHERE date > $1
                    GROUP BY token_ticker, network
                    ORDER BY mention_count DESC, avg_confidence DESC
                    LIMIT 10
                """,
                    naive_utc_date - time_window,
                )
                return trending_tokens
            except Exception as e:
                print(f"An error occurred: {e}")
                return None


db = Database()
