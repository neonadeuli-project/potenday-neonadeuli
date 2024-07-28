import secrets
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, HTTPException
from datetime import timedelta

from app.core.deps import get_db    
from app.repository.user_repository import UserRepository
from app.utils.common import get_unique_nickname
from app.models.user import User
from app.core.security import create_access_token 

class UserService:
    def __init__(self, db: AsyncSession):
        self.user_repository = UserRepository(db)

    # Random Token 임시 유저 생성    

    # 헤더 Token 기반 임시 유저 생성
    async def create_temp_user(self, username: str) -> User:
        # token = secrets.token_urlsafe(32)
        user = await self.user_repository.create_temp_user(name=username, token=None)

        if user is None:
            raise HTTPException(status_code=400, detail="Failed to create user")

        access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=timedelta(hours=1)
        )
        
        updated_user = await self.user_repository.update_user_token(user.id, access_token)
        
        if updated_user is None:
            raise HTTPException(status_code=400, detail="Failed to update user token")
        
        return user
    
    async def get_user_by_token(self, token: str) -> User:
        return await self.user_repository.get_user_by_token(token)
    
    # 유저 토큰 삭제
    async def invalidate_token(self, token: str) -> bool:
        user = await self.user_repository.get_user_by_token(token)
        if user:
            user.token = None
            updated_user = await self.user_repository.update_user(user)
            return updated_user is not None
        return False