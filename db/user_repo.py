from typing import Optional, Dict, Any, List
from db.base_repo import PostgresRepository
from db.utils import logger, json_serial
from asyncpg import UniqueViolationError
from datetime import datetime
import json


class UserRepository(PostgresRepository):
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        try:
            return await self.fetchrow("SELECT * FROM users WHERE email = $1", email)
        except Exception as e:
            logger.error(f"Error fetching user by email: {e}")
            return None

    async def get_user_by_wallet(self, wallet_address: str) -> Optional[Dict[str, Any]]:
        try:
            return await self.fetchrow(
                "SELECT * FROM users WHERE wallet_address = $1", wallet_address
            )
        except Exception as e:
            logger.error(f"Error fetching user by wallet: {e}")
            return None

    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        try:
            return await self.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
        except Exception as e:
            logger.error(f"Error fetching user by id: {e}")
            return None

    async def update_user_wallet(
        self, user_id: int, wallet_address: str
    ) -> Optional[Dict[str, Any]]:
        try:
            return await self.fetchrow(
                """
                UPDATE users
                SET wallet_address = $2
                WHERE id = $1
                RETURNING *
                """,
                user_id,
                wallet_address,
            )
        except Exception as e:
            logger.error(f"Error updating user wallet: {e}")
            return None

    async def update_payout_option(
        self, user_id: int, payout_option: str
    ) -> Optional[Dict[str, Any]]:
        try:
            return await self.fetchrow(
                """
                UPDATE users
                SET payout_option = $2
                WHERE id = $1
                RETURNING *
                """,
                user_id,
                payout_option,
            )
        except Exception as e:
            logger.error(f"Error updating user payout option: {e}")
            return None

    async def update_user_email(
        self, user_id: int, email: str
    ) -> Optional[Dict[str, Any]]:
        try:
            return await self.fetchrow(
                """
                UPDATE users
                SET email = $2
                WHERE id = $1
                RETURNING *
                """,
                user_id,
                email,
            )
        except Exception as e:
            logger.error(f"Error updating user email: {e}")
            return None

    async def create_user(
        self,
        email: Optional[str],
        wallet_address: Optional[str],
        referred_by_user_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        try:
            return await self.fetchrow(
                """
                INSERT INTO users (email, wallet_address, role, referred_by_user_id)
                VALUES ($1, $2, $3, $4)
                RETURNING *
                """,
                email,
                wallet_address,
                "basic",
                referred_by_user_id,
            )
        except UniqueViolationError:
            logger.warning(
                f"Attempt to create duplicate user: {email or wallet_address}"
            )
            return None
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None

    async def update_user_role(
        self,
        user_id: int,
        role: str,
        stripe_customer_id: Optional[str] = None,
        stripe_subscription_id: Optional[str] = None,
        subscription_end_date: Optional[datetime] = None,
    ) -> Optional[Dict[str, Any]]:
        try:
            return await self.fetchrow(
                """
                UPDATE users
                SET role = $2, stripe_customer_id = $3, stripe_subscription_id = $4, subscription_end_date = $5
                WHERE id = $1
                RETURNING *
                """,
                user_id,
                role,
                stripe_customer_id,
                stripe_subscription_id,
                subscription_end_date,
            )
        except Exception as e:
            logger.error(f"Error updating user role and subscription info: {e}")
            return None

    async def crypto_update_user_role(
        self,
        user_id: int,
        role: str,
        crypto_customer_id: Optional[str] = None,
        subscription_end_date: Optional[datetime] = None,
    ) -> Optional[Dict[str, Any]]:
        try:
            return await self.fetchrow(
                """
                UPDATE users
                SET role = $2, crypto_customer_id = $3, subscription_end_date = $4
                WHERE id = $1
                RETURNING *
                """,
                user_id,
                role,
                crypto_customer_id,
                subscription_end_date,
            )
        except Exception as e:
            logger.error(f"Error updating crypto user role and subscription info: {e}")
            return None

    async def update_subscription_end_date(
        self, subscription_id: str, subscription_end_date: datetime
    ) -> Optional[Dict[str, Any]]:
        try:
            return await self.fetchrow(
                """
                UPDATE users
                SET subscription_end_date = $2
                WHERE stripe_subscription_id = $1
                RETURNING *
                """,
                subscription_id,
                subscription_end_date,
            )
        except Exception as e:
            logger.error(f"Error updating subscription end date: {e}")
            return None

    async def update_user_role_by_subscription(
        self, stripe_subscription_id: str, role: str
    ) -> Optional[Dict[str, Any]]:
        try:
            return await self.fetchrow(
                """
                UPDATE users
                SET role = $2, stripe_subscription_id = NULL, subscription_end_date = NULL
                WHERE stripe_subscription_id = $1
                RETURNING *
                """,
                stripe_subscription_id,
                role,
            )
        except Exception as e:
            logger.error(f"Error updating user role by subscription: {e}")
            return None

    async def update_user_affiliate_code(
        self, user_id: int, affiliate_code: str
    ) -> Optional[Dict[str, Any]]:
        try:
            return await self.fetchrow(
                """
                UPDATE users SET affiliate_code = $1
                WHERE id = $2
                RETURNING *
                """,
                affiliate_code,
                user_id,
            )
        except Exception as e:
            logger.error(f"Error updating user affiliate code: {e}")
            return None

    async def get_user_by_affiliate_code(
        self, affiliate_code: str
    ) -> Optional[Dict[str, Any]]:
        try:
            return await self.fetchrow(
                "SELECT * FROM users WHERE affiliate_code = $1", affiliate_code
            )
        except Exception as e:
            logger.error(f"Error getting user by affiliate code: {e}")
            return None

    async def create_referral(
        self, referrer_id: int, referred_id: int
    ) -> Optional[Dict[str, Any]]:
        try:
            return await self.fetchrow(
                """
                INSERT INTO referrals (referrer_id, referred_id)
                VALUES ($1, $2)
                RETURNING *
                """,
                referrer_id,
                referred_id,
            )
        except Exception as e:
            logger.error(f"Error creating referral: {e}")
            return None

    async def create_commission(
        self, referrer_id: int, referred_id: int, amount: float
    ) -> Optional[Dict[str, Any]]:
        try:
            return await self.fetchrow(
                """
                INSERT INTO commissions (referrer_id, referred_id, amount)
                VALUES ($1, $2, $3)
                RETURNING *
                """,
                referrer_id,
                referred_id,
                amount,
            )
        except Exception as e:
            logger.error(f"Error creating commission: {e}")
            return None

    async def get_referrals(self, user_id: int) -> List[Dict[str, Any]]:
        cache_key = f"referrals:{user_id}"
        if self.db.redis:
            try:
                cached_data = await self.db.redis.get(cache_key)
                if cached_data:
                    logger.info("Returning cached result")
                    return [dict(referral) for referral in json.loads(cached_data)]
            except Exception as e:
                logger.error(f"Cache error: {e}")
        try:
            referrals = await self.fetch(
                """
                SELECT * FROM referrals
                WHERE referrer_id = $1
                """,
                user_id,
            )

            if self.db.redis:
                try:
                    await self.db.redis.set(
                        cache_key,
                        json.dumps(
                            [dict(referral) for referral in referrals],
                            default=json_serial,
                        ),
                        ex=60 * 5,
                    )
                except Exception as e:
                    logger.error(f"Failed to cache referrals: {e}")

            return referrals
        except Exception as e:
            logger.error(f"Error fetching referrals: {e}")
            return []

    async def get_commissions(self, user_id: int) -> List[Dict[str, Any]]:
        cache_key = f"commissions:{user_id}"
        if self.db.redis:
            try:
                cached_data = await self.db.redis.get(cache_key)
                if cached_data:
                    logger.info("Returning cached result")
                    return [dict(commission) for commission in json.loads(cached_data)]
            except Exception as e:
                logger.error(f"Cache error: {e}")

        try:
            commissions = await self.fetch(
                """
                SELECT * FROM commissions
                WHERE referrer_id = $1
                """,
                user_id,
            )

            if self.db.redis:
                try:
                    await self.db.redis.set(
                        cache_key,
                        json.dumps(
                            [dict(commission) for commission in commissions],
                            default=json_serial,
                        ),
                        ex=60 * 5,
                    )
                except Exception as e:
                    logger.error(f"Failed to cache commissions: {e}")

            return commissions
        except Exception as e:
            logger.error(f"Error fetching commissions: {e}")
            return []
