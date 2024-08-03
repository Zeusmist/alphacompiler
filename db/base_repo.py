from abc import ABC, abstractmethod
from typing import Any, Optional


class Repository(ABC):
    def __init__(self, db):
        self.db = db

    @abstractmethod
    async def execute(self, query: str, *args) -> Any:
        pass

    @abstractmethod
    async def fetch(self, query: str, *args) -> list[Any]:
        pass

    @abstractmethod
    async def fetchrow(self, query: str, *args) -> Optional[Any]:
        pass


class PostgresRepository(Repository):
    async def execute(self, query: str, *args) -> Any:
        async with self.db.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args) -> list[Any]:
        async with self.db.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args) -> Optional[Any]:
        async with self.db.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
