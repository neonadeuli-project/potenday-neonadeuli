import json
import logging
from typing import Callable, List
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.core.config import settings
from app.service.clova_service import ClovaService
from app.repository.chat_repository import ChatRepository
from app.repository.user_repository import UserRepository

logger = logging.getLogger(__name__)

class ChatService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repository = UserRepository(db)
        self.chat_repository = ChatRepository(db)
        self.clova_service = ClovaService()
    
    # 채팅 세션 생성하기
    async def create_chat_session(self, user_id: int, heritage_id: int):
        logger.info(f"ChatService에서 채팅 세션 생성을 시도합니다. (user_id: {user_id}, heritage_id: {heritage_id})")
        async with self.db.begin():
            try:
                return await self.chat_repository.create_chat_session(user_id, heritage_id)
            except Exception as e:
                logger.error(f"create_chat_session 메소드 에러 발생: {str(e)}", exc_info=True)
                raise

    # async def update_conversation(self, session_id: int, content: str):
    #     # 기존 대화 내용 가져오기
    #     chat_session = await self.chat_repository.get_chat_session(session_id)
    #     full_conversation = json.loads(chat_session.full_conversation) if chat_session.full_conversation else []
    #     sliding_window = json.loads(chat_session.sliding_window) if chat_session.sliding_window else []

    #     # 사용자 메시지 저장
    #     user_message = await self.chat_repository.create_message(session_id, "user", content)

    #     # full_conversation & sliding_window 업데이트
    #     full_conversation.append({"role": "user", "content": content})
    #     sliding_window.append({"role": "user", "content": content})

    #     # 네이버 클로바 API 호출
    #     bot_response = await self.clova_service.get_clova(session_id, sliding_window) 

    #     # 챗봇 메시지 저장
    #     bot_message = await self.chat_repository.create_message(session_id, "assistant", bot_response)

    #     # full_conversation & sliding_window  다시 업데이트
    #     full_conversation.append({"role": "assistant", "content": bot_response})
    #     sliding_window.append({"role": "assistant", "content": bot_response})

    #     # 슬라이딩 윈도우 크기 제한
    #     max_window_size = settings.MAX_SLIDING_WINDOW_SIZE
    #     if len(sliding_window) > max_window_size:
    #         sliding_window = sliding_window[-max_window_size:]

    #     # 업데이트 된 대화 내용 저장
    #     await self.chat_repository.update_message(
    #         session_id,
    #         full_conversation=json.dumps(full_conversation, ensure_ascii=False),
    #         sliding_window=json.dumps(sliding_window, ensure_ascii=False)
    #     )

    #     return user_message, bot_message
         
    # 채팅 대화 내용 업데이트
    async def update_conversation(self, session_id: int, content: str, clova_method: Callable):
        # 기존 대화 내용 가져오기
        chat_session = await self.chat_repository.get_chat_session(session_id)
        full_conversation = json.loads(chat_session.full_conversation) if chat_session.full_conversation else []
        sliding_window = json.loads(chat_session.sliding_window) if chat_session.sliding_window else []

        logger.debug(f"Current sliding window: {sliding_window}")
        
        # User 메시지 저장
        await self.update_conversation_content(session_id, "user", content, full_conversation, sliding_window)
        
        # Clova API 호출
        clova_responses = await self.get_clova_response(clova_method, session_id, sliding_window)
        bot_response = clova_responses["response"]
        new_sliding_window = clova_responses["new_sliding_window"]

        # Clova 메시지 저장
        await self.update_conversation_content(session_id, "assistant", bot_response, full_conversation, sliding_window)


        # 슬라이딩 윈도우 크기 제한
        # sliding_window = self.limit_sliding_window(sliding_window)

        # 업데이트 된 대화 내용 저장
        await self.save_conversation(session_id, full_conversation, new_sliding_window)

        return bot_response
    
    # 대화 내용 업데이트
    async def update_conversation_content(self, session_id: int, role: str, content: str, full_conversation: list, sliding_window: list):
        content_str = json.dumps(content, ensure_ascii=False) if isinstance(content, dict) else content
        message = await self.chat_repository.create_message(session_id, role, content_str)
        full_conversation.append({"role": role, "content": content_str})
        sliding_window.append({"role": role, "content": content_str})
        return message
    
    # Clova 응답 조회
    async def get_clova_response(self, clova_method: Callable, session_id: int, sliding_window: list, *args, **kwargs) -> str:
        response = await clova_method(session_id, sliding_window)
        return response
    
    # 슬라이딩 윈도우 크기 제한
    # def limit_sliding_window(self, sliding_window: list) -> list:
    #     max_window_size = settings.MAX_SLIDING_WINDOW_SIZE
    #     return sliding_window[-max_window_size:] if len(sliding_window) > max_window_size else sliding_window
    
    # 업데이트 된 대화 내용 저장
    async def save_conversation(self, session_id: int, full_conversation: list, sliding_window: list):
        await self.chat_repository.update_message(
            session_id,
            full_conversation=json.dumps(full_conversation, ensure_ascii=False),
            sliding_window=json.dumps(sliding_window, ensure_ascii=False)
        )

    # 채팅 세션 종료하기
    async def end_chat_session(self, session_id: int):
        logger.info(f"ChatService에서 채팅 세션 종료를 시도합니다. (session_id: {session_id})")
        async with self.db.begin():
            try:
                return await self.chat_repository.update_session(session_id)
            except Exception as e:
                logger.error(f"end_chat_session 메소드 에러 발생: {str(e)}", exc_info=True)
                raise

    # 채팅 메시지 메서드
    async def update_chat_conversation(self, session_id: int, content: str):
        # 사용자 메시지 저장 및 Clova 응답 받기
        bot_response =  await self.update_conversation(session_id, content, self.clova_service.get_chatting)

        # 가장 최근 챗봇 메시지 조회 
        # 최근 메시지 뿐 아니라 연관된 다른 컬럼 데이터도 가져올 수 있기 때문에 bot_response와 구분
        bot_message = await self.chat_repository.get_latest_message(session_id, "assistant")
        
        if bot_message is None:
            raise ValueError("대화 업데이트 이후 챗봇 메시지를 찾을 수 없습니다.")

        return {
            "id": bot_message.id,
            "session_id": session_id,
            "role": "assistant",
            "content": bot_response,
            "timestamp": bot_message.timestamp.isoformat()
        }

    # # 건축물 퀴즈 제공 메서드
    # async def update_quiz_conversation(self, session_id: int, content: str):
    #     return await self.update_conversation(session_id, content, self.clova_service.get_quiz)

    # # 채팅 요약 메서드
    # async def update_summary_conversation(self, session_id: int, content: str):
    #     return await self.update_conversation(session_id, content, self.clova_service.get_summary)