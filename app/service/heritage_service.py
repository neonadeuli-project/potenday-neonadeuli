import logging

from typing import List
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from haversine import haversine
from app.error.heritage_exceptions import DatabaseConnectionError, HeritageNotFoundException, InvalidCoordinatesException
from app.repository.heritage_repository import HeritageRepository
from app.schemas.heritage import HeritageDetailResponse, HeritageListResponse
from pygeodesic import geodesic

logger = logging.getLogger(__name__)

class HeritageService:
    def __init__(self, db: AsyncSession):
        self.heritage_repository = HeritageRepository(db)

    # 문화재 리스트 조회
    async def get_heritages(self, page: int, limit: int, user_latitude: float, user_longitude) -> List[HeritageListResponse]:
        try:
            offset = (page - 1) * limit
            heritages = await self.heritage_repository.search_heritages(limit, offset)
        except SQLAlchemyError as e:
            logger.error(f"Database error in get_heritages: {str(e)}")
            raise DatabaseConnectionError()

        user_location = (user_latitude, user_longitude)
        result = []
        for heritage in heritages:
            try:
                if heritage.latitude is not None and heritage.longitude is not None:
                    heritage_location = (float(heritage.latitude), float(heritage.longitude))
                    distance = round(haversine(user_location, heritage_location), 1)
                else:
                    raise InvalidCoordinatesException(heritage.id)
            except (ValueError, TypeError) as e:
                distance = None
                logger.error(f"문화재 ID가 {heritage.id}인 문화재의 거리 계산을 실패했습니다. : {str(e)}")
                distance = None
            except InvalidCoordinatesException as e:
                logger.warning(str(e))
                distance = None
                

            result.append(HeritageListResponse(
                id = heritage.id,
                name = heritage.name,
                location = heritage.location,
                heritage_type = heritage.heritage_types.name,
                image_url = heritage.image_url,
                distance = distance
            ))

        return result
    
    # 문화재 상세 조회
    async def get_heritage_by_id(self, heritage_id: int) -> HeritageDetailResponse:
        try:
            heritage = await self.heritage_repository.get_heritage_by_id(heritage_id)
            if not heritage:
                raise HeritageNotFoundException(heritage_id)
        except SQLAlchemyError as e:
            logger.error(f"Database error in get_heritage_detail: {str(e)}")
            raise DatabaseConnectionError()
        
        return HeritageDetailResponse (
            id = heritage.id,
            image_url = heritage.image_url,
            name = heritage.name,
            name_hanja = heritage.name_hanja,
            description = heritage.description,
            heritage_type = heritage.heritage_types.name if heritage.heritage_types else None,
            category = heritage.category,
            sub_category1 = heritage.sub_category1,
            sub_category2 = heritage.sub_category2,
            era = heritage.era,
            location = heritage.location
        )