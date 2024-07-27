import logging
import asyncio
from typing import Optional
from functools import lru_cache

from app.core.deps import get_db    
from app.service.chat_service import ClovaService, ChatService
from app.models.heritage.heritage_building import HeritageBuilding
from app.models.heritage.heritage_building_image import HeritageBuildingImage
from app.repository.heritage_repository import HeritageRepository
from app.repository.chat_repository import ChatRepository
from app.models.heritage.heritage_type import HeritageType

logger = logging.getLogger(__name__)

class HeritageService:
    def __init__(self, chat_service: ChatService, heritage_repository: HeritageRepository, chat_repository: ChatRepository, clova_service: ClovaService):
        self.chat_service = chat_service
        self.chat_repository = chat_repository
        self.heritage_repository = heritage_repository
        self.clova_service = clova_service

    # 문화재 건축물 정보 제공
    async def get_heritage_building_info(self, session_id: int, building_id: int, content: str = None):
        # 세션 및 유효성 검사
        await self.validate_session_and_building(session_id, building_id) 

        # 해당 건축물의 이미지 조회 
        # image_url = await self.get_building_image_url(building_id)
        image_url_task = asyncio.create_task(self.get_building_image_url(building_id))
        bot_response_task = asyncio.create_task(self.chat_service.update_conversation(session_id, content, self.clova_service.get_chatting))
        # Clova 챗봇 응답 조회
        # bot_response = None
        # if content:
        #     bot_response = await self.chat_service.update_conversation(session_id, content, self.clova_service.get_chatting)

        image_url = await image_url_task
        bot_response = await bot_response_task if bot_response_task else None

        return image_url, bot_response
    
    @lru_cache(maxsize=100)
    async def get_building_image_url(self, building_id: int) -> Optional[str]:
        images = await self.heritage_repository.get_heritage_building_images(building_id)
        return images[0].image_url if images else None
    
    # 문화재 건축물 퀴즈 제공
    async def get_heritage_building_quiz(self, session_id: int, building_id: int, content: str):
        # 세션 및 유효성 검사
        building = await self.validate_session_and_building(session_id, building_id) 
        
        # Clova 챗봇 퀴즈 생성 및 대화 업데이트
        quiz_response = await self.chat_service.update_quiz_conversation(session_id, content)

        return quiz_response

    # 세션 및 유효성 검사 메서드
    async def validate_session_and_building(self, session_id: int, building_id: int):
        chat_session = await self.chat_service.chat_repository.get_chat_session(session_id)
        if not chat_session:
            raise ValueError(f"세션 ID {session_id}인 채팅 세션을 찾을 수 없습니다.")

        building = await self.heritage_repository.get_heritage_building_by_id(building_id)
        if not building:
            raise ValueError(f"건축물 ID {building_id}인 건축물을 찾을 수 없습니다.")

        if building.heritage_id != chat_session.heritage_id:
            raise ValueError("요청된 건축물과 채팅 방이 연관되어 있지 않습니다.")

        return building

    # 참고 엔티티
    # def create_building_info(self, building: HeritageBuilding, images: list[HeritageBuildingImage]):
    #     building_type : HeritageType = building.building_types
    #     return {
    #         "id": building.id,
    #         "name": building.name,
    #         "description": building.description,
    #         "latitude": float(building.latitude),
    #         "longitude": float(building.longitude),
    #         "custom_radius": building.custom_radius,
    #         "building_type": building_type.element_type if building.building_types else None,
    #         "heritage_name": building.name,
    #         "images": [
    #             {
    #                 "url": image.image_url,
    #                 "description": image.description,
    #                 "alt_text": image.alt_text,
    #                 "order": image.order
    #             } for image in images
    #         ]
    #     }
    

    # async def get_heritage_or_building_images(self, heritage_id: int = None, building_id: int = None):
    #     if heritage_id:
    #         return await self.repository.get_heritage_images(heritage_id)
    #     elif building_id:
    #         return await self.repository.get_building_images(building_id)
    #     else:
    #         raise ValueError("Either heritage_id or building_id must be provided")