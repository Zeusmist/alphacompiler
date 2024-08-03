from typing import Optional, List, Dict, Any
import aiohttp
from datetime import datetime, timezone, timedelta
from dateutil.parser import parse
import json
from db.db_operations import PostgresRepository, logger, json_serial


class TokenRepository(PostgresRepository):
    async def save_alpha_call(self, alpha_call: Dict[str, Any]):
        date = parse(alpha_call["date"])
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        else:
            date = date.astimezone(timezone.utc)

        naive_utc_date = date.replace(tzinfo=None)

        await self.execute(
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

    async def get_trending_tokens(
        self, time_window: timedelta, limit: int = 10
    ) -> List[Dict[str, Any]]:
        cache_key = f"trending_tokens:{time_window}:{limit}"

        if self.db.redis:
            try:
                cached_data = await self.db.redis.get(cache_key)
                if cached_data:
                    logger.info("Returning cached result")
                    return json.loads(cached_data)
            except Exception as e:
                logger.error(f"Cache error: {e}")

        try:
            now = datetime.now(timezone.utc)
            naive_utc_date = now.replace(tzinfo=None)
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
            rows = await self.fetch(query, naive_utc_date - time_window, limit)

            trending_tokens = []
            async with aiohttp.ClientSession() as session:
                for row in rows:
                    token_data = dict(row)
                    token_address = token_data["token_address"]
                    dex_url = (
                        f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
                    )

                    try:
                        async with session.get(dex_url) as response:
                            if response.status == 200:
                                dex_data = await response.json()
                                if dex_data["pairs"] and len(dex_data["pairs"]) > 0:
                                    pair = dex_data["pairs"][0]
                                    token_data.update(
                                        {
                                            "pair": f"{pair['baseToken']['symbol']}/{pair['quoteToken']['symbol']}",
                                            "price": pair.get("priceUsd", 0),
                                            "24h_change": pair["priceChange"]["h24"],
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

            if self.db.redis:
                try:
                    await self.db.redis.set(
                        cache_key,
                        json.dumps(trending_tokens, default=json_serial),
                        ex=60 * 5,
                    )
                except Exception as e:
                    logger.error(f"Failed to set redis: {e}")

            return trending_tokens

        except Exception as e:
            logger.error(f"An error occurred: {e}")
            return []

    async def get_network_for_ticker(self, ticker: str) -> Optional[str]:
        try:
            result = await self.fetchrow(
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
            return result["network"] if result else None
        except Exception as e:
            logger.error(f"An error occurred while fetching network for ticker: {e}")
            return None
