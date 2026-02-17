"""Model checking endpoints. Phase 3 implementation."""

from fastapi import APIRouter, Depends

from src.auth.middleware import get_current_user
from src.auth.models import User

router = APIRouter()


@router.post("/{slug}/check/validate")
async def run_validation(slug: str, user: User = Depends(get_current_user)):
    return {"message": "Model checking available in Phase 3"}


@router.get("/{slug}/check/results")
async def list_results(slug: str, user: User = Depends(get_current_user)):
    return {"message": "Model checking available in Phase 3", "results": []}
