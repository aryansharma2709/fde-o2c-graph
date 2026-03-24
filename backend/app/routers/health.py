from typing import Dict

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["health"])

router = APIRouter()


@router.get("/health")
def health_check() -> Dict[str, str]:
    return {"status": "ok"}