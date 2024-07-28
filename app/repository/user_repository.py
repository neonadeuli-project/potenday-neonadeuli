from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime

from app.models.user import User

class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # 임시 로그인 유저 저장
    async def create_user(self, name: str, token: str) -> User:
        user = User(
            name=name,
            token=token,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def get_user_by_name(self, name: str) -> User:
        # return self.db.query(User).filter(User.name == name).first()
        result = await self.db.execute(select(User).where(User.name == name))
        return result.scalars().first()
    
    async def get_user_by_id(self, user_id: int) -> User:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalars().first()

    async def get_user_by_token(self, token: str) -> User:
        result = await self.db.execute(select(User).where(User.token == token))
        return result.scalars().first()