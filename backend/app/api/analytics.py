"""
Rutas de analytics (placeholder)
"""

from fastapi import APIRouter, Depends
from app.api.auth import get_current_user
from app.models import UserResponse

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/stats")
async def get_basic_stats(current_user: UserResponse = Depends(get_current_user)):
    """Obtener estadísticas básicas"""
    return {
        "message": "Analytics module - coming soon",
        "user": current_user.username
    }