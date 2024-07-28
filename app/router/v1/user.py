import logging
import secrets
import string

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_token    
from app.schemas.user import UserValidationResponse, UserTempLoginResponse, UserLogoutResponse
from app.service.user_service import UserService

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# 임시 로그인
@router.post("/login", response_model=UserTempLoginResponse)
async def temp_login(db: AsyncSession = Depends(get_db)):
    user_service = UserService(db)
    
    # 랜덤 닉네임 생성
    random_username = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
    
    try:
        # 임시 유저 생성
        user = await user_service.create_temp_user(random_username)
        if user is None:
            raise HTTPException(status_code=400, detail="Failed to create temporary user")
        
        return UserTempLoginResponse (
            id=user.id,
            username=user.name,
            access_token=user.token,
            token_type="bearer"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# 토큰 검증
@router.get("/validate_token", response_model=UserValidationResponse)
async def validate_token(token: str = Depends(get_token), db: AsyncSession = Depends(get_db)):
    user_service = UserService(db)

    user = await user_service.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=404, detail="유효하지 않은 토큰입니다.")

    return UserValidationResponse(
        id=user.id,
        username=user.name,
        created_at=user.created_at
    )

#로그아웃
@router.post("/logout")
async def logout(token: str = Depends(get_token), db: AsyncSession = Depends(get_db)):
    user_service = UserService(db)
    success = await user_service.invalidate_token(token)
    
    if success:
        return UserLogoutResponse(
            message="로그아웃 성공",
            success=success
        )
    else:
        raise HTTPException(status_code=400, detail="로그인 실패")