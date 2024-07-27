from fastapi import FastAPI
from datetime import timedelta
from db_operations import db

app = FastAPI()


@app.on_event("startup")
async def startup():
    await db.connect()


@app.on_event("shutdown")
async def shutdown():
    await db.close()


@app.get("/trending_tokens")
async def get_trending_tokens(time_window: str = "24h"):
    # Convert time_window to timedelta
    if time_window == "24h":
        window = timedelta(hours=24)
    elif time_window == "7d":
        window = timedelta(days=7)
    else:
        window = timedelta(days=3)  # Default to 3 days

    trending_tokens = await db.get_trending_tokens(window, limit=10)
    return {"trending_tokens": trending_tokens}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run()
