import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User, ApiToken
from src.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_jwt_token(user_id: str, username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": str(user_id),
        "username": username,
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_jwt_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None


def generate_api_token() -> tuple[str, str]:
    """Generate a raw token and its hash. Returns (raw_token, token_hash)."""
    raw = f"ifcgit_{secrets.token_urlsafe(32)}"
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    return raw, token_hash


async def register_user(db: AsyncSession, username: str, email: str, password: str, role: str = "viewer") -> User:
    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, username: str, password: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user and verify_password(password, user.password_hash):
        return user
    return None


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_token_hash(db: AsyncSession, token_hash: str) -> User | None:
    result = await db.execute(
        select(User)
        .join(ApiToken, ApiToken.user_id == User.id)
        .where(ApiToken.token_hash == token_hash)
        .where(
            (ApiToken.expires_at.is_(None)) | (ApiToken.expires_at > datetime.now(timezone.utc))
        )
    )
    return result.scalar_one_or_none()


async def create_api_token_for_user(
    db: AsyncSession, user_id: uuid.UUID, name: str, expires_days: int | None = None
) -> tuple[str, ApiToken]:
    raw_token, token_hash = generate_api_token()
    expires_at = None
    if expires_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_days)
    token = ApiToken(user_id=user_id, token_hash=token_hash, name=name, expires_at=expires_at)
    db.add(token)
    await db.commit()
    await db.refresh(token)
    return raw_token, token


async def delete_api_token(db: AsyncSession, token_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(ApiToken).where(ApiToken.id == token_id, ApiToken.user_id == user_id)
    )
    token = result.scalar_one_or_none()
    if token:
        await db.delete(token)
        await db.commit()
        return True
    return False
