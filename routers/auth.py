from fastapi import APIRouter, Depends, HTTPException
from models.user_models import User, UserSignup
from fastapi import Depends, HTTPException, status
from user_operations import (
    get_user_by_email,
    get_user_by_wallet,
    create_user,
    create_access_token,
    get_user_by_affiliate_code,
    create_referral,
)
from pydantic import BaseModel
from datetime import timedelta
from helpers.api_helpers import (
    get_user_by_identifier,
    get_current_user,
)
from models.user_models import User, UserSignup
from lib.config import access_token_expire_minutes

router = APIRouter()


class TokenUser(BaseModel):
    access_token: str
    user: User


class TokenRequest(BaseModel):
    identifier: str  # This can be either email or wallet address


def get_access_token(identifier: str):
    return create_access_token(
        data={"sub": identifier},
        expires_delta=timedelta(minutes=access_token_expire_minutes),
    )


@router.post("/token", response_model=TokenUser)
async def login_for_access_token(token_request: TokenRequest):
    user = await get_user_by_identifier(token_request.identifier)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found. Please sign up",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = get_access_token(user.email or user.wallet_address)
    return {
        "access_token": access_token,
        "user": user,
    }


@router.post("/signup", response_model=TokenUser)
async def signup(user: UserSignup):
    if user.email:
        existing_user = await get_user_by_email(user.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
    elif user.wallet_address:
        existing_wallet = await get_user_by_wallet(user.wallet_address)
        if existing_wallet:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Wallet address already registered",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either email or wallet address must be provided",
        )

    referred_by_user_id = None
    if user.affiliate_code:
        affiliate = await get_user_by_affiliate_code(user.affiliate_code)
        if affiliate:
            referred_by_user_id = affiliate["id"]

    new_user = await create_user(user.email, user.wallet_address, referred_by_user_id)

    if referred_by_user_id:
        await create_referral(referred_by_user_id, new_user["id"])

    access_token = get_access_token(user.email or user.wallet_address)

    return {
        "access_token": access_token,
        "user": new_user,
    }


@router.get("/login", response_model=TokenUser)
async def connect_wallet(current_user: User = Depends(get_current_user)):
    access_token = get_access_token(current_user.email or current_user.wallet_address)
    return {
        "access_token": access_token,
        "user": current_user,
    }
