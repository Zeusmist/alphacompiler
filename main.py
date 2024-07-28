import asyncio
from telegram_client import start_telegram_client
from api import app
import uvicorn
from service_starter import main as start_services


async def run_api():
    config = uvicorn.Config(app, host="localhost", port=8000, loop="asyncio")
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    await asyncio.gather(start_telegram_client(), run_api())


if __name__ == "__main__":
    start_services()
    asyncio.run(main())
