import logging
from typing import List, Optional

from fastapi import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, values
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload
from datetime import datetime

from app.models.chat.chat_session import ChatSession
from app.models.chat.chat_message import ChatMessage
from app.models.user import User
from app.models.heritage.heritage_building_image import HeritageBuildingImage
from app.models.heritage.heritage_building import HeritageBuilding
from app.models.heritage.heritage import Heritage

logger = logging.getLogger(__name__)

class HeritageRepository:
    
    def __init__ (self, db: AsyncSession):
        self.db = db
    
    # 문화재 건축물 ID 조회
    async def get_heritage_building_by_id(self, building_id: int) -> Optional[HeritageBuilding]:
        result = await self.db.execute(select(HeritageBuilding)
                                       .where(HeritageBuilding.id == building_id)
                                       .options(
                                           joinedload(HeritageBuilding.building_types),
                                           joinedload(HeritageBuilding.heritages)
                                       ))
        return result.scalars().first()
    
    # 문화재 건축물 이미지 조회
    async def get_heritage_building_images(self, building_id: int) -> List[HeritageBuildingImage]:
        result = await self.db.execute(select(HeritageBuildingImage)
                                       .where(HeritageBuildingImage.building_id == building_id)
                                       .order_by(HeritageBuildingImage.order))
        return result.scalars().all()
    

        