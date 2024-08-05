from typing import Optional, Dict, Any
from db.base_repo import PostgresRepository
from db.utils import logger
from asyncpg import UniqueViolationError
from datetime import datetime


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
                RETURNING id, email, wallet_address
                """,
                user_id,
                wallet_address,
            )
        except Exception as e:
            logger.error(f"Error updating user wallet: {e}")
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
                RETURNING id, email, wallet_address
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
    ) -> Optional[Dict[str, Any]]:
        try:
            return await self.fetchrow(
                """
                INSERT INTO users (email, wallet_address, role)
                VALUES ($1, $2, $3)
                RETURNING *
                """,
                email,
                wallet_address,
                "basic",
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
                RETURNING id, email, wallet_address, role, stripe_customer_id, stripe_subscription_id, subscription_end_date
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

    async def update_subscription_end_date(
        self, subscription_id: str, subscription_end_date: datetime
    ) -> Optional[Dict[str, Any]]:
        try:
            return await self.fetchrow(
                """
                UPDATE users
                SET subscription_end_date = $2
                WHERE stripe_subscription_id = $1
                RETURNING id, email, subscription_end_date
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
                RETURNING id, email, role
                """,
                stripe_subscription_id,
                role,
            )
        except Exception as e:
            logger.error(f"Error updating user role by subscription: {e}")
            return None
