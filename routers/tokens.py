from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from datetime import timedelta
from db.db_operations import db_operations
from helpers.api_helpers import get_current_user
from models.user_models import User

router = APIRouter()


@router.get("/trending_tokens")
async def get_trending_tokens(
    time_window: str = "24h",
    current_user: Optional[User] = Depends(get_current_user),
    limit: int = 10,
    sort_by: str = "mention_count",
    sort_order: str = "desc",
):
    limit = limit if current_user and current_user.role == "premium" else 3

    # if time window ends with h, use hours, if time window ends with d, use days
    if time_window[-1] == "h":
        window = timedelta(hours=int(time_window[:-1]))
    elif time_window[-1] == "d":
        window = timedelta(days=int(time_window[:-1]))
    else:
        window = timedelta(days=3)

    window = (
        window if current_user and current_user.role == "premium" else timedelta(days=7)
    )

    # # Convert time_window to timedelta
    # if time_window == "24h":
    #     window = timedelta(hours=24)
    # elif time_window == "7d":
    #     window = timedelta(days=7)
    # else:
    #     window = timedelta(days=3)  # Default to 3 days

    try:
        trending_tokens = await db_operations.token_repo.get_trending_tokens(
            window,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        return {"trending_tokens": trending_tokens}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
