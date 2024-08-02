from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime

from app.error.auth_exception import UserNotFoundException
from app.models.user import User

class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # 임시 로그인 유저 저장
    async def create_temp_user(self, name: str, token: str) -> User:
        new_user = User(
            name=name,
            token=token,
            created_at=datetime.now(),
            last_login=datetime.now()
        )
        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)
        return new_user

    async def get_user_by_name(self, name: str) -> User:
        result = await self.db.execute(select(User).where(User.name == name))
        return result.scalars().first()
    
    async def get_user_by_id(self, user_id: int) -> User:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalars().first()

    async def get_user_by_token(self, token: str) -> User:
        result = await self.db.execute(select(User).where(User.token == token))
        user = result.scalars().first()
        if not user:
            raise UserNotFoundException(f"토큰: {token}")
        return user
    
    async def update_user_token(self, user_id: int, token: str) -> User:
        try:
            user = await self.db.get(User, user_id)
            if not user:
                raise UserNotFoundException(f"ID: {user_id}")
            user.token = token
            await self.db.commit()
            await self.db.refresh(user)
            return user
        except Exception as e:
            await self.db.rollback()
            print(f"유저 토큰 업데이트 에러: {e}")
            raise
    
    async def update_user(self, user: User) -> User:
        try:
            await self.db.commit()
            await self.db.refresh(user)  # user 객체를 인자로 전달
            return user
        except Exception as e:
            await self.db.rollback()
            print(f"Error updating user: {e}")
            return None