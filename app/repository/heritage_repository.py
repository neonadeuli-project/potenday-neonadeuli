import logging
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, values, join
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload, aliased

from app.models.heritage.heritage_building_image import HeritageBuildingImage
from app.models.heritage.heritage_building import HeritageBuilding
from app.models.heritage.heritage_route import HeritageRoute
from app.models.heritage.heritage_route_building import HeritageRouteBuilding
from app.models.heritage.heritage import Heritage
from app.schemas.heritage import HeritageRouteInfo, HeritageBuildingInfo

logger = logging.getLogger(__name__)

class HeritageRepository:
    
    def __init__ (self, db: AsyncSession):
        self.db = db

    # 문화재 ID 조회
    async def get_heritage_by_id(self, heritage_id: int) -> Heritage:
        result = await self.db.execute(select(Heritage)
                                       .where(Heritage.id == heritage_id))
        return result.scalar_one()
    
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
    
    # 문화재 건축물 코스 조회
    async def get_routes_with_buildings_by_heritages_id(self, heritage_id: int) -> List[HeritageRouteInfo]:
        result = await self.db.execute(select(HeritageRoute)
                                       .options(joinedload(HeritageRoute.route_buildings)
                                                .joinedload(HeritageRouteBuilding.buildings))
                                        .where(HeritageRoute.heritage_id == heritage_id))

        routes = result.unique().scalars().all()

        return [
            HeritageRouteInfo(
                route_id=route.id,
                name=route.name,
                buildings=[
                    HeritageBuildingInfo(
                        building_id=rb.buildings.id, 
                        name=rb.buildings.name,
                        coordinate=(rb.buildings.longitude, rb.buildings.latitude)
                    )
                    for rb in sorted(route.route_buildings, key=lambda x: x.visit_order)
                ]
            )
            for route in routes
        ]
