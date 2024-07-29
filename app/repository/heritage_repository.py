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
    async def get_routes_with_buildings_by_heritages_id(self, heritage_id: int):
        HeritageRouteAlias = aliased(HeritageRoute)
        HeritageBuildingAlias = aliased(HeritageBuilding)

        result = await self.db.execute(select(
                                    HeritageRouteAlias.id.label('route_id'),
                                    HeritageRouteAlias.name.label('route_name'),
                                    HeritageBuildingAlias.id.label('building_id'),
                                    HeritageBuildingAlias.name.label('building_name')
                                )
                                .join(HeritageRouteBuilding, HeritageRouteAlias.id == HeritageRouteBuilding.route_id)
                                .join(HeritageBuildingAlias, HeritageRouteBuilding.building_id == HeritageBuildingAlias.id)
                                .where(HeritageRouteAlias.heritage_id == heritage_id)
                                .order_by(HeritageRouteAlias.id, HeritageRouteBuilding.visit_order))
        
        rows = result.fetchall()

        routes = {}
        for row in rows:
            if row.route_id not in routes:
                routes[row.route_id] = {
                    "id": row.route_id,
                    "name": row.route_name,
                    "buildings": []
                }
            routes[row.route_id]["buildings"].append({
                "id": row.building_id,
                "name": row.building_name
            })

        return list(routes.values())
