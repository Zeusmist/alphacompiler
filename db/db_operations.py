from typing import Optional, Any
import asyncpg
from lib.config import (
    pg_user,
    pg_password,
    pg_host,
    pg_database,
    redis_host,
    redis_port,
    redis_db,
)
from aioredis import Redis
from abc import ABC, abstractmethod
from db.user_repo import UserRepository
from db.token_repo import TokenRepository
from db.utils import logger


class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.redis: Optional[Redis] = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def connect(self):
        self.pool = await asyncpg.create_pool(
            user=pg_user,
            password=pg_password,
            database=pg_database,
            host=pg_host,
        )
        async with self.pool.acquire() as conn:
            await conn.execute("SET timezone TO 'UTC';")

        self.redis = Redis(
            host=redis_host, port=redis_port, db=redis_db, encoding="utf-8"
        )
        await self.redis.set("test_key", "test_value")
        value = await self.redis.get("test_key")
        logger.info(f"Retrieved value from Redis: {value}")

        logger.info("Database connected and Redis initialized")

    async def close(self):
        if self.pool:
            await self.pool.close()
        if self.redis:
            await self.redis.close()
        logger.info("Database connection closed")


class DatabaseOperations:
    def __init__(self, db: Database):
        self.db = db
        self.user_repo = UserRepository(db)
        self.token_repo = TokenRepository(db)

    async def connect(self):
        await self.db.connect()

    async def close(self):
        await self.db.close()


db_operations = DatabaseOperations(Database())
