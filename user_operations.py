from typing import Optional
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from pydantic import BaseModel
from db_operations import db
from lib.config import secret_key, token_algorithm, access_token_expire_minutes

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = secret_key
ALGORITHM = token_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = access_token_expire_minutes


class User(BaseModel):
    id: int
    email: Optional[str] = None
    wallet_address: Optional[str] = None


class UserInDB(User):
    hashed_password: Optional[str] = None


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


async def get_user_by_email(email: str):
    user = await db.get_user_by_email(email)
    if user:
        return UserInDB(**user)


async def get_user_by_wallet(wallet_address: str):
    user = await db.get_user_by_wallet(wallet_address)
    if user:
        return UserInDB(**user)


async def create_user(
    email: Optional[str], password: Optional[str], wallet_address: Optional[str]
):
    hashed_password = get_password_hash(password) if password else None
    user = await db.create_user(email, hashed_password, wallet_address)
    return User(**user)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
