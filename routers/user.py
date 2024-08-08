from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from db.db_operations import db_operations
from user_operations import (
    get_user_by_email,
    get_user_by_wallet,
    generate_unique_affiliate_code,
    get_user_by_affiliate_code,
)
from helpers.api_helpers import get_current_user
from models.user_models import User


router = APIRouter()


class UpdateUser(BaseModel):
    email: Optional[str] = None
    wallet_address: Optional[str] = None
    payout_option: Optional[str] = None


@router.post("/connect_wallet")
async def connect_wallet(
    request: UpdateUser, current_user: User = Depends(get_current_user)
):
    existing_wallet = await get_user_by_wallet(request.wallet_address)
    if existing_wallet:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Wallet address already registered",
        )
    updated_user = await db_operations.user_repo.update_user_wallet(
        current_user.id, request.wallet_address
    )
    return {"wallet_address": request.wallet_address, "updated_user": updated_user}


@router.post("/connect_email")
async def connect_email(
    request: UpdateUser, current_user: User = Depends(get_current_user)
):
    existing_user = await get_user_by_email(request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    updated_user = await db_operations.user_repo.update_user_email(
        current_user.id, request.email
    )
    return {"email": request.email, "updated_user": updated_user}


@router.post("/join-affiliate")
async def join_affiliate(current_user: User = Depends(get_current_user)):
    if current_user.affiliate_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already an affiliate",
        )

    while True:
        affiliate_code = generate_unique_affiliate_code()
        existing_user = await get_user_by_affiliate_code(affiliate_code)
        if not existing_user:
            break

    updated_user = await db_operations.user_repo.update_user_affiliate_code(
        current_user.id, affiliate_code
    )

    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user",
        )

    return {"affiliate_code": affiliate_code, "updated_user": updated_user}


@router.get("/referrals")
async def get_referrals(current_user: User = Depends(get_current_user)):
    referrals = await db_operations.user_repo.get_referrals(current_user.id)
    commissions = await db_operations.user_repo.get_commissions(current_user.id)

    total_earned = sum(c["amount"] for c in commissions if c["status"] == "paid")
    pending_payout = sum(c["amount"] for c in commissions if c["status"] == "pending")

    return {
        "referrals_count": len(referrals),
        "total_earned": total_earned,
        "pending_payout": pending_payout,
    }


@router.post("/change_payout_option")
async def change_payout_option(
    request: UpdateUser, current_user: User = Depends(get_current_user)
):
    if request.payout_option not in ["USDT", "USDC"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payout option",
        )

    updated_user = await db_operations.user_repo.update_payout_option(
        current_user.id, request.payout_option
    )

    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user",
        )

    return {"payout_option": request.payout_option, "updated_user": updated_user}
