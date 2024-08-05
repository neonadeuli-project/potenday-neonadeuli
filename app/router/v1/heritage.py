# 로깅 설정
import logging
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, Query

from app.core.deps import get_db
from app.schemas.heritage import HeritageListResponse
from app.service.heritage_service import HeritageService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/search", response_model=List[HeritageListResponse])
async def list_heritages(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    user_latitude: float = Query(..., ge=-90, le=90),
    user_longitude: float = Query(..., ge=-180, le=180)
):
    heritage_service = HeritageService(db)
    heritages = await heritage_service.get_heritages(page, limit, user_latitude, user_longitude)
    return heritages