import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.auth.models import User, ApiToken
from src.auth.service import (
    register_user,
    authenticate_user,
    create_jwt_token,
    create_api_token_for_user,
    delete_api_token,
)
from src.auth.erpnext import (
    encrypt_secret,
    decrypt_secret,
    test_erpnext_connection,
    test_nextcloud_connection,
)
from src.config import settings
from src.db.database import get_db

router = APIRouter()


# --- Schemas ---

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    role: str

    model_config = {"from_attributes": True}


class CreateApiTokenRequest(BaseModel):
    name: str
    expires_days: int | None = None


class ApiTokenResponse(BaseModel):
    id: uuid.UUID
    name: str | None
    token: str | None = None  # Only returned on creation
    expires_at: str | None
    created_at: str

    model_config = {"from_attributes": True}


# --- Endpoints ---

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check existing
    existing = await db.execute(
        select(User).where((User.username == req.username) | (User.email == req.email))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username or email already taken")

    # First user gets admin role
    user_count = await db.execute(select(User))
    role = "admin" if not user_count.scalars().first() else "viewer"

    user = await register_user(db, req.username, req.email, req.password, role=role)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_jwt_token(str(user.id), user.username)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return user


@router.post("/tokens", response_model=ApiTokenResponse, status_code=status.HTTP_201_CREATED)
async def create_token(
    req: CreateApiTokenRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    raw_token, token = await create_api_token_for_user(db, user.id, req.name, req.expires_days)
    return ApiTokenResponse(
        id=token.id,
        name=token.name,
        token=raw_token,
        expires_at=token.expires_at.isoformat() if token.expires_at else None,
        created_at=token.created_at.isoformat(),
    )


@router.get("/tokens", response_model=list[ApiTokenResponse])
async def list_tokens(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ApiToken).where(ApiToken.user_id == user.id))
    tokens = result.scalars().all()
    return [
        ApiTokenResponse(
            id=t.id,
            name=t.name,
            expires_at=t.expires_at.isoformat() if t.expires_at else None,
            created_at=t.created_at.isoformat(),
        )
        for t in tokens
    ]


@router.delete("/tokens/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_token(
    token_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    deleted = await delete_api_token(db, token_id, user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Token not found")


# --- Settings Schemas ---

class SettingsResponse(BaseModel):
    username: str
    email: str
    role: str
    erpnext_url: str | None = None
    erpnext_api_key: str | None = None
    erpnext_api_secret_set: bool = False
    nextcloud_url: str | None = None
    nextcloud_username: str | None = None
    nextcloud_password_set: bool = False


class SettingsUpdateRequest(BaseModel):
    erpnext_url: str | None = None
    erpnext_api_key: str | None = None
    erpnext_api_secret: str | None = None
    nextcloud_url: str | None = None
    nextcloud_username: str | None = None
    nextcloud_password: str | None = None


# --- Settings Endpoints ---

@router.get("/settings", response_model=SettingsResponse)
async def get_settings(user: User = Depends(get_current_user)):
    return SettingsResponse(
        username=user.username,
        email=user.email,
        role=user.role,
        erpnext_url=user.erpnext_url,
        erpnext_api_key=user.erpnext_api_key,
        erpnext_api_secret_set=bool(user.erpnext_api_secret),
        nextcloud_url=user.nextcloud_url,
        nextcloud_username=user.nextcloud_username,
        nextcloud_password_set=bool(user.nextcloud_password),
    )


@router.put("/settings", response_model=SettingsResponse)
async def update_settings(
    req: SettingsUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if req.erpnext_url is not None:
        user.erpnext_url = req.erpnext_url or None
    if req.erpnext_api_key is not None:
        user.erpnext_api_key = req.erpnext_api_key or None
    if req.erpnext_api_secret is not None:
        user.erpnext_api_secret = encrypt_secret(req.erpnext_api_secret, settings.secret_key) if req.erpnext_api_secret else None
    if req.nextcloud_url is not None:
        user.nextcloud_url = req.nextcloud_url or None
    if req.nextcloud_username is not None:
        user.nextcloud_username = req.nextcloud_username or None
    if req.nextcloud_password is not None:
        user.nextcloud_password = encrypt_secret(req.nextcloud_password, settings.secret_key) if req.nextcloud_password else None

    await db.commit()
    await db.refresh(user)

    return SettingsResponse(
        username=user.username,
        email=user.email,
        role=user.role,
        erpnext_url=user.erpnext_url,
        erpnext_api_key=user.erpnext_api_key,
        erpnext_api_secret_set=bool(user.erpnext_api_secret),
        nextcloud_url=user.nextcloud_url,
        nextcloud_username=user.nextcloud_username,
        nextcloud_password_set=bool(user.nextcloud_password),
    )


@router.post("/settings/erpnext/test")
async def test_erpnext(user: User = Depends(get_current_user)):
    if not user.erpnext_url or not user.erpnext_api_key or not user.erpnext_api_secret:
        raise HTTPException(status_code=400, detail="ERPNext credentials not configured")
    api_secret = decrypt_secret(user.erpnext_api_secret, settings.secret_key)
    if not api_secret:
        raise HTTPException(status_code=400, detail="Failed to decrypt API secret")
    result = await test_erpnext_connection(user.erpnext_url, user.erpnext_api_key, api_secret)
    return result


@router.post("/settings/nextcloud/test")
async def test_nextcloud(user: User = Depends(get_current_user)):
    if not user.nextcloud_url or not user.nextcloud_username or not user.nextcloud_password:
        raise HTTPException(status_code=400, detail="Nextcloud credentials not configured")
    password = decrypt_secret(user.nextcloud_password, settings.secret_key)
    if not password:
        raise HTTPException(status_code=400, detail="Failed to decrypt password")
    result = await test_nextcloud_connection(user.nextcloud_url, user.nextcloud_username, password)
    return result
