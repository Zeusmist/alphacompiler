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

    async def get_trending_tokens(self, time_window):
        async with self.pool.acquire() as conn:
            now = datetime.now(timezone.utc)
            naive_utc_date = now.replace(tzinfo=None)
            # use a try catch to get the trending tokens
            try:
                trending_tokens = await conn.fetch(
                    """
                    WITH ranked_tokens AS (
                        SELECT 
                            token_ticker, 
                            network, 
                            token_address,
                            COUNT(*) as mention_count,
                            MAX(date) as latest_date
                        FROM alpha_calls
                        WHERE date > $1
                        GROUP BY token_ticker, network, token_address
                    )
                    SELECT 
                        rt.token_ticker, 
                        rt.network, 
                        rt.token_address,
                        ac.token_name,
                        ac.token_image,
                        rt.mention_count,
                        rt.latest_date
                    FROM ranked_tokens rt
                    JOIN alpha_calls ac ON 
                        rt.token_ticker = ac.token_ticker AND
                        rt.network = ac.network AND
                        rt.token_address = ac.token_address AND
                        rt.latest_date = ac.date
                    ORDER BY rt.mention_count DESC, rt.latest_date DESC
                    LIMIT 10
                """,
                    naive_utc_date - time_window,
                )
                return trending_tokens
            except Exception as e:
                print(f"An error occurred: {e}")
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


db = Database()
