from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr, validator, root_validator
from datetime import timedelta
from db_operations import db
from user_operations import (
    get_user_by_email,
    get_user_by_wallet,
    create_user,
    create_access_token,
)
from lib.config import secret_key, token_algorithm, access_token_expire_minutes
from helpers.api import authenticate_user, get_current_user

app = FastAPI()

SECRET_KEY = secret_key  # Change this to a secure random key
ALGORITHM = token_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = access_token_expire_minutes

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


class Token(BaseModel):
    access_token: str
    token_type: str


class User(BaseModel):
    email: Optional[str] = None
    wallet_address: Optional[str] = None


class UserInDB(User):
    hashed_password: str


class UserSignup(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    wallet_address: Optional[str] = None

    @root_validator(pre=True)
    def check_email_or_wallet(cls, values):
        email = values.get("email")
        wallet_address = values.get("wallet_address")
        if not email and not wallet_address:
            raise ValueError("Either email or wallet_address must be provided")
        if email and not values.get("password"):
            raise ValueError("Password is required when email is provided")
        return values

    # @validator("email", "wallet_address")
    # def check_email_or_wallet(cls, v, values):
    #     if not values.get("email") and not values.get("wallet_address"):
    #         raise ValueError("Either email or wallet_address must be provided")
    #     return v

    @validator("password")
    def check_password(cls, v, values):
        if values.get("email") and not v:
            raise ValueError("Password is required when email is provided")
        return v


@app.on_event("startup")
async def startup():
    await db.connect()


@app.on_event("shutdown")
async def shutdown():
    await db.close()


@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/signup")
async def signup(user: UserSignup):
    print(f"User: {user}")
    if user.email:
        existing_user = await get_user_by_email(user.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
    if user.wallet_address:
        existing_wallet = await get_user_by_wallet(user.wallet_address)
        if existing_wallet:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Wallet address already registered",
            )

    new_user = await create_user(user.email, user.password, user.wallet_address)
    return {"message": "User created successfully", "user_id": new_user.id}


@app.post("/connect_wallet")
async def connect_wallet(
    wallet_address: str, current_user: User = Depends(get_current_user)
):
    existing_wallet = await get_user_by_wallet(wallet_address)
    if existing_wallet:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Wallet address already registered",
        )
    updated_user = await db.update_user_wallet(current_user.email, wallet_address)
    return {"message": "Wallet connected successfully", "user": updated_user}


@app.get("/trending_tokens")
async def get_trending_tokens(
    time_window: str = "24h", token: Optional[str] = Depends(oauth2_scheme)
):
    # Convert time_window to timedelta
    if time_window == "24h":
        window = timedelta(hours=24)
    elif time_window == "7d":
        window = timedelta(days=7)
    else:
        window = timedelta(days=3)  # Default to 3 days

    limit = 10

    try:
        if token:
            user = await get_current_user(token)
            # User is authenticated, return 10 tokens
        else:
            # User is not authenticated, return 3 tokens
            limit = 3
    except HTTPException:
        # Token is invalid, treat as unauthenticated
        limit = 3

    trending_tokens = await db.get_trending_tokens(window, limit=limit)
    return {"trending_tokens": trending_tokens}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
