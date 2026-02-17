"""Clash detection endpoints. Phase 2 implementation."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.auth.middleware import get_current_user
from src.auth.models import User

router = APIRouter()


@router.get("/{slug}/clash/sets")
async def list_clash_sets(slug: str, user: User = Depends(get_current_user)):
    return {"message": "Clash detection available in Phase 2", "sets": []}


@router.post("/{slug}/clash/detect")
async def run_clash_detection(slug: str, user: User = Depends(get_current_user)):
    return {"message": "Clash detection available in Phase 2"}
