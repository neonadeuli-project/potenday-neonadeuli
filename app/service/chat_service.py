import json
import logging

from typing import Any, Callable, Dict, List
from fastapi import HTTPException

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.models.enums import RoleType
from app.repository.heritage_repository import HeritageRepository
from app.service.clova_service import ClovaService
from app.repository.chat_repository import ChatRepository
from app.repository.user_repository import UserRepository
from app.schemas.chat import ChatSessionResponse, ChatMessageResponse, ChatSessionEndResponse

logger = logging.getLogger(__name__)

class ChatService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repository = UserRepository(db)
        self.chat_repository = ChatRepository(db)
        self.heritage_repository = HeritageRepository(db)
        self.clova_service = ClovaService()
    
    # 채팅 세션 생성하기
    async def create_chat_session(self, user_id: int, heritage_id: int):
        logger.info(f"ChatService에서 채팅 세션 생성을 시도합니다. (user_id: {user_id}, heritage_id: {heritage_id})")
        async with self.db.begin():
            try:
                # 채팅 세션 생성하기
                new_session = await self.chat_repository.create_chat_session(user_id, heritage_id)

                # 문화재 정보 가져오기
                heritage = await self.heritage_repository.get_heritage_by_id(heritage_id)
                routes = await self.heritage_repository.get_routes_with_buildings_by_heritages_id(heritage_id)

                return ChatSessionResponse(
                    session_id=new_session.id,
                    start_time=new_session.start_time,
                    created_at=new_session.created_at,
                    heritage_id=heritage.id,
                    heritage_name=heritage.name,
                    routes=routes
                )
            except Exception as e:
                logger.error(f"create_chat_session 메소드 에러 발생: {str(e)}", exc_info=True)
                raise
    
    # 채팅 세션 종료하기
    async def end_chat_session(self, session_id: int) -> ChatSessionEndResponse:
        logger.info(f"ChatService에서 채팅 세션 종료를 시도합니다. (session_id: {session_id})")
        try:
            ended_session = await self.chat_repository.end_chat_session(session_id)

            # 세션을 찾지 못했거나 이미 종료된 경우
            if ended_session is None:
                raise HTTPException(status_code=404, detail="활성화 된 세션을 찾을 수 없음")
            
            # TODO: 채팅 요약 서비스 추가 별도 메소드로 할지 요약 API와 같이 처리할지 논의 필요

            return ChatSessionEndResponse (
                id = ended_session.id,
                user_id = ended_session.user_id,
                heritage_id=ended_session.heritage_id,
                start_time=ended_session.start_time,
                end_time=ended_session.end_time,
                created_at=ended_session.created_at,
                updated_at=ended_session.updated_at
            )
                
        except SQLAlchemyError as e:
            raise HTTPException(status_code=500, detail="데이터 베이스 오류 발생")
        except Exception as e:
            raise HTTPException(status_code=500, detail="예상치 못한 에러 발생")
         
    # 채팅 대화 내용 업데이트
    async def update_conversation(self, session_id: int, content: str, clova_method: Callable):
        # 기존 대화 내용 가져오기
        chat_session = await self.chat_repository.get_chat_session(session_id)
        full_conversation = json.loads(chat_session.full_conversation) if chat_session.full_conversation else []
        sliding_window = json.loads(chat_session.sliding_window) if chat_session.sliding_window else []

        logger.debug(f"Current sliding window: {sliding_window}")
        
        # User 메시지 저장
        await self.update_conversation_content(session_id, RoleType.USER, content, full_conversation, sliding_window)
        
        # Clova API 호출
        clova_responses = await self.get_clova_response(clova_method, session_id, sliding_window)
        bot_response = clova_responses["response"]
        new_sliding_window = clova_responses["new_sliding_window"]

        # Clova 메시지 저장
        await self.update_conversation_content(session_id, RoleType.ASSISTANT, bot_response, full_conversation, sliding_window)

        # 업데이트 된 대화 내용 저장
        await self.save_conversation(session_id, full_conversation, new_sliding_window)

        return bot_response
    
    # 대화 내용 업데이트
    async def update_conversation_content(self, session_id: int, role: RoleType, content: str, full_conversation: list, sliding_window: list):
        content_str = json.dumps(content, ensure_ascii=False) if isinstance(content, dict) else content
        message = await self.chat_repository.create_message(session_id, role, content_str)
        full_conversation.append({"role": role.value, "content": content_str})
        sliding_window.append({"role": role.value, "content": content_str})
        return message
    
    # Clova 응답 조회
    async def get_clova_response(self, clova_method: Callable, session_id: int, sliding_window: list, *args, **kwargs) -> str:
        response = await clova_method(session_id, sliding_window)
        return response
    
    # 업데이트 된 대화 내용 저장
    async def save_conversation(self, session_id: int, full_conversation: list, sliding_window: list):
        await self.chat_repository.update_message(
            session_id,
            full_conversation=json.dumps(full_conversation, ensure_ascii=False),
            sliding_window=json.dumps(sliding_window, ensure_ascii=False)
        )

    # 채팅 메시지 메서드
    async def update_chat_conversation(self, session_id: int, content: str) -> ChatMessageResponse:
        # 사용자 메시지 저장 및 Clova 응답 받기
        bot_response =  await self.update_conversation(session_id, content, self.clova_service.get_chatting)

        # 가장 최근 챗봇 메시지 조회 
        # 최근 메시지 뿐 아니라 연관된 다른 컬럼 데이터도 가져올 수 있기 때문에 bot_response와 구분
        bot_message = await self.chat_repository.get_latest_message(session_id, RoleType.ASSISTANT)
        
        if bot_message is None:
            raise ValueError("대화 업데이트 이후 챗봇 메시지를 찾을 수 없습니다.")

        return ChatMessageResponse (
            id=bot_message.id,
            session_id=session_id,
            role=RoleType.ASSISTANT.value,
            content=bot_response,
            timestamp=bot_message.timestamp
        )
    
    # 퀴즈 제공 메서드
    async def update_quiz_conversation(self, session_id: int, building_id: int) -> Dict[str, Any]:
        building = await self.heritage_repository.get_heritage_building_by_id(building_id)
        if not building:
            raise ValueError(f"Building with id {building_id} not found")

        quiz_response = await self.clova_service.get_quiz(session_id, building.name)
        quiz_text = quiz_response["quiz_text"]
        options = quiz_response["options"]
        new_sliding_window = quiz_response["new_sliding_window"]

        # 기존 대화 내용 가져오기
        chat_session = await self.chat_repository.get_chat_session(session_id)
        full_conversation = json.loads(chat_session.full_conversation) if chat_session.full_conversation else []
        sliding_window = json.loads(chat_session.sliding_window) if chat_session.sliding_window else []
        
        # 퀴즈 내용을 채팅 세션에 저장
        await self.update_conversation_content(session_id, "assistant", quiz_text, full_conversation, sliding_window)

        # 업데이트 된 대화 내용 저장
        await self.save_conversation(session_id, full_conversation, new_sliding_window)

        return {
            "quiz_text": quiz_text,
            "options": options,
        }
    
    def parse_quiz_response(self, response: str) -> Dict[str, Any]:
        lines = response.split("\n")
        quiz_text = lines[0]
        options = lines[1:6]  # Assuming the options are on lines 1 to 5

        return {
            "quiz_text": quiz_text,
            "options": options,
        }

    # # 채팅 요약 메서드
    # async def update_summary_conversation(self, session_id: int, content: str):
    #     return await self.update_conversation(session_id, content, self.clova_service.get_summary)
