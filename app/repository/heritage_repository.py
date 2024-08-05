import json
import logging
from typing import Any, Dict, List, Optional, Tuple

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
from app.models.quiz import Quiz
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
    
    # 문화재 이름 조회
    async def get_heritage_building_name_by_id(self, building_id: int) -> str:
        result = await self.db.execute(select(HeritageBuilding.name)
                                       .where(HeritageBuilding.id == building_id)
                                    )
        return result.scalar_one_or_none()

    # 문화재 건축물 ID 조회
    async def get_heritage_building_by_id(self, building_id: int) -> Optional[HeritageBuilding]:
        result = await self.db.execute(select(HeritageBuilding)
                                       .where(HeritageBuilding.id == building_id)
                                       .options(
                                           joinedload(HeritageBuilding.building_types),
                                           joinedload(HeritageBuilding.heritages))
                                        )
        return result.scalars().first()
    
    # 문화재 건축물 이미지 조회
    async def get_heritage_building_images(self, building_id: int) -> List[HeritageBuildingImage]:
        result = await self.db.execute(select(HeritageBuildingImage)
                                       .options(joinedload(HeritageBuildingImage.buildings))
                                       .where(HeritageBuildingImage.building_id == building_id)
                                       .order_by(HeritageBuildingImage.image_order))
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
    
    # 문화재 건축물 퀴즈 조회
    async def get_quiz_by_id(self, quiz_id: int):
        quiz = await self.db.execute(select(Quiz)
                                     .where(Quiz.id == quiz_id))
        return quiz.scalar_one_or_none()
    
    # 문화재 건축물 퀴즈 저장
    async def save_quiz_data(self, session_id: int, parsed_quiz: Dict[str, Any]):
        quiz = Quiz(
            session_id = session_id,
            question=parsed_quiz['question'],
            options=json.dumps(parsed_quiz['options'], ensure_ascii=False),
            answer=parsed_quiz['answer'],
            explanation=parsed_quiz['explanation']
        )
        self.db.add(quiz)
        await self.db.commit()
        await self.db.refresh(quiz)
        return quiz
    
    # 문화재에 속한 건축물 검증
    async def verify_building_belongs_to_heritage(self, heritage_id: int, building_id: int) -> bool:
        verified_building = await self.db.execute(select(HeritageBuilding)
                                                  .where(
                                                      (HeritageBuilding.id == building_id) &
                                                      (HeritageBuilding.heritage_id == heritage_id)
                                                  )
                                                )
        return verified_building.scalar_one_or_none() is not None
    
    # 문화재 리스트 조회
    async def search_heritages(self, limit: int, offset: int):
        result = await self.db.execute(select(Heritage)
                                       .options(joinedload(Heritage.heritage_types))
                                       .order_by(Heritage.id)
                                       .limit(limit)
                                       .offset(offset)
                                    )
        return result.unique().scalars().all()