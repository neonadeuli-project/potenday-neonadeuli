import secrets
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.deps import get_db    
from app.schemas.user import UserTempLoginResponse
from app.service.user_service import UserService

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/login", response_model=UserTempLoginResponse)
async def temp_login(db: AsyncSession = Depends(get_db)):
    user_service = UserService(db)
    user = await user_service.create_temporary_user()

    response = UserTempLoginResponse (
        nickname=user.name,
        access_token=secrets.token_urlsafe(32),
        token_type="bearer",
        expires_in=3600
    )

    return response