from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.core.deps import get_db    
from app.repository.user_repository import UserRepository
from app.utils.common import get_unique_nickname

class UserService:
    def __init__(self, db: AsyncSession):
        self.user_repository = UserRepository(db)

    # 임시 유저 생성
    async def create_temporary_user(self) -> str:
        nickname = await get_unique_nickname(self.user_repository.db)
        user = await self.user_repository.create_user(name=nickname)
        return user