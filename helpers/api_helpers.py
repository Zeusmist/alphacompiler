from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from user_operations import (
    get_user_by_email,
    get_user_by_wallet,
    is_premium_user,
)
from lib.config import secret_key, jwt_algorithm
from models.user_models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class TokenData(BaseModel):
    identifier: Optional[str] = None


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, secret_key, algorithms=[jwt_algorithm])
        identifier: str = payload.get("sub")
        if identifier is None:
            raise credentials_exception
        token_data = TokenData(identifier=identifier)
    except JWTError:
        raise credentials_exception
    user = await get_user_by_identifier(token_data.identifier)
    if user is None:
        raise credentials_exception
    return user


async def get_user_by_identifier(identifier: str):
    print(f"get_user_by_identifier: {identifier}")
    user = await get_user_by_email(identifier)
    if user is None:
        user = await get_user_by_wallet(identifier)

    print(f"get_user_by_identifier USER: {user}")
    return user


async def get_premium_user(current_user: User = Depends(get_current_user)):
    if not is_premium_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium subscription required",
        )
    return current_user
