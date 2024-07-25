from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from korean_name_generator import namer
   
from app.models.user import User

# 생성 가능한 이름이 한정되어 있으므로 개발 초기에만 사용
def generate_random_korean_name(length=8):
    name_generator = namer.generate(True)
    return name_generator

async def get_unique_nickname(db: AsyncSession):
    while True:
        nickname = generate_random_korean_name()
        result = await db.execute(select(User).where(User.name == nickname))
        # Check if the nickname already exists in the database
        if not result.scalars().first():
            return nickname