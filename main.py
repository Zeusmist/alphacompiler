import asyncio
from telegram_client import start_telegram_client
from api import app
import uvicorn
from service_starter import main as start_services
from db.db_operations import db_operations


async def run_api():
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, loop="asyncio")
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    await asyncio.gather(run_api(), start_telegram_client())


if __name__ == "__main__":
    start_services()
    asyncio.run(main())
