import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.deps import get_db    
from app.schemas.user import UserResponse, UserTempLoginResponse
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
        user_id=user.id,
        name=user.name,
        access_token=user.token,
        token_type="bearer",
        expires_in=3600
    )

    return response

@router.get("/user_by_token", response_model=UserResponse)
async def get_user_by_token(token: str, db: AsyncSession = Depends(get_db)):
    user_service = UserService(db)
    user = await user_service.get_user_by_token(token)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user
