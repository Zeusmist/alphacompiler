from typing import Optional
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from db.db_operations import db_operations
from lib.config import secret_key, jwt_algorithm
from models.user_models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

user_repo = db_operations.user_repo


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


async def get_user_by_email(email: str):
    user = await user_repo.get_user_by_email(email)
    if user:
        return User(**user)


async def get_user_by_wallet(wallet_address: str):
    user = await user_repo.get_user_by_wallet(wallet_address)
    if user:
        return User(**user)


async def create_user(email: Optional[str], wallet_address: Optional[str]):
    user = await user_repo.create_user(email, wallet_address)
    return User(**user)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=jwt_algorithm)
    return encoded_jwt


def is_premium_user(user: User):
    return user.role == "premium" or (
        user.subscription_end_date and user.subscription_end_date > datetime.utcnow()
    )
