import json
import logging
from typing import List
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
         
    # 채팅 대화 내용 업데이트
    async def update_conversation(self, session_id: int, content: str):
        # 기존 대화 내용 가져오기
        chat_session = await self.chat_repository.get_chat_session(session_id)
        full_conversation = json.loads(chat_session.full_conversation) if chat_session.full_conversation else []
        sliding_window = json.loads(chat_session.sliding_window) if chat_session.sliding_window else []

        # 사용자 메시지 저장
        user_message = await self.chat_repository.create_message(session_id, "user", content)
        
        # full_conversation & sliding_window 업데이트
        full_conversation.append({"role": "user", "content": content})
        sliding_window.append({"role": "user", "content": content})
        
        # 네이버 클로바 API 호출
        # TODO: AI Service Class 만들기
        bot_response = await self.clova_service.get_clova(session_id, sliding_window) 

        # 챗봇 메시지 저장
        bot_message = await self.chat_repository.create_message(session_id, "bot", bot_response)

        # full_conversation & sliding_window  다시 업데이트
        full_conversation.append({"role": "bot", "content": bot_response})
        sliding_window.append({"role": "bot", "content": bot_response})

        # 슬라이딩 윈도우 크기 제한
        max_window_size = settings.MAX_SLIDING_WINDOW_SIZE
        if len(sliding_window) > max_window_size:
            sliding_window = sliding_window[-max_window_size:]

        # 업데이트 된 대화 내용 저장
        await self.chat_repository.update_message(
            session_id,
            full_conversation=json.dumps(full_conversation, ensure_ascii=False),
            sliding_window=json.dumps(sliding_window, ensure_ascii=False)
        )

        return user_message, bot_message

    # 채팅 세션 종료하기
    async def end_chat_session(self, session_id: int):
        logger.info(f"ChatService에서 채팅 세션 종료를 시도합니다. (session_id: {session_id})")
        async with self.db.begin():
            try:
                return await self.chat_repository.update_session(session_id)
            except Exception as e:
                logger.error(f"end_chat_session 메소드 에러 발생: {str(e)}", exc_info=True)
                raise
