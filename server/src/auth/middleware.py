import hashlib
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.auth.service import decode_jwt_token, get_user_by_id, get_user_by_token_hash
from src.db.database import get_db

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    token = credentials.credentials

    # Try JWT first
    payload = decode_jwt_token(token)
    if payload:
        user_id = payload.get("sub")
        if user_id:
            user = await get_user_by_id(db, uuid.UUID(user_id))
            if user:
                return user

    # Try API token
    if token.startswith("ifcgit_"):
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        user = await get_user_by_token_hash(db, token_hash)
        if user:
            return user

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    if not credentials:
        return None
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


def require_role(*roles: str):
    async def check_role(user: User = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user
    return check_role
