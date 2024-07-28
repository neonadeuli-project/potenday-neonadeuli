from fastapi import HTTPException, Header

from app.core.database import AsyncSessionLocal

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
        await session.commit()
        # with을 사용하면 알아서 session을 닫아줌
        # await session.close()

async def get_token(Authorization: str = Header(None)):
    if not Authorization:
        raise HTTPException(status_code=401, detail="Authorization Header missing")
    scheme, token = Authorization.split()
    if scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization scheme")
    return token