import logging

from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from haversine import haversine
from app.repository.heritage_repository import HeritageRepository
from app.schemas.heritage import HeritageListResponse
from pygeodesic import geodesic

logger = logging.getLogger(__name__)

class HeritageService:
    def __init__(self, db: AsyncSession):
        self.heritage_repository = HeritageRepository(db)

    async def get_heritages(self, page: int, limit: int, user_latitude: float, user_longitude) -> List[HeritageListResponse]:
        offset = (page - 1) * limit
        heritages = await self.heritage_repository.search_heritages(limit, offset)

        user_location = (user_latitude, user_longitude)
        result = []
        for heritage in heritages:
            try:
                if heritage.latitude is not None and heritage.longitude is not None:
                    heritage_location = (float(heritage.latitude), float(heritage.longitude))
                    distance = round(haversine(user_location, heritage_location), 1)
                else:
                    distance = None
                    logger.warning(f"문화재 ID가 {heritage.id}인 문화재는 위도, 경도 값이 없습니다.")
            except (ValueError, TypeError) as e:
                distance = None
                logger.error(f"문화재 ID가 {heritage.id}인 문화재의 거리 계산을 실패했습니다. : {str(e)}")
                

            result.append(HeritageListResponse(
                id = heritage.id,
                name = heritage.name,
                location = heritage.location,
                heritage_type = heritage.heritage_types.name,
                image_url = heritage.image_url,
                distance = distance
            ))
            
        return result

