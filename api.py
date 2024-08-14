from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.db_operations import db_operations
from lib.config import allowed_origins
from routers import auth, user, subscription, tokens


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(user.router)
app.include_router(subscription.router)
app.include_router(tokens.router)


@app.on_event("startup")
async def startup():
    await db_operations.connect()


@app.on_event("shutdown")
async def shutdown():
    await db_operations.token_repo.cleanup()
    await db_operations.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
