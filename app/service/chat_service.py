import json
import logging
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.repository.chat_repository import ChatRepository
from app.repository.user_repository import UserRepository

logger = logging.getLogger(__name__)

class ChatService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repository = UserRepository(db)
        self.chat_repository = ChatRepository(db)
    
    # 채팅 세션 생성하기
    async def create_chat_session(self, user_id: int, heritage_id: int):
        logger.info(f"Attempting to create chat session for user_id: {user_id}, heritage_id: {heritage_id}")
        async with self.db.begin():
            try:
                return await self.chat_repository.create_chat_session(user_id, heritage_id)
            except Exception as e:
                logger.error(f"Error in create_chat_session: {str(e)}", exc_info=True)
                raise
    
    # 채팅 메시지 생성하기
    async def create_chat_message(self, session_id: int, message_text: str, sender: str):
        return await self.chat_repository.create_chat_message(session_id, message_text, sender)
    
    # 모든 채팅 대화 내역 조회하기
    async def get_full_conversation(self, session_id: int) -> List[dict]:
        chat_session = await self.chat_repository.get_chat_session(session_id)
        return json.loads(chat_session.full_conversation)
    
    # 채팅 대화 내용 업데이트
    async def update_conversation(self, session_id: int, new_message: dict):
        chat_session = await self.chat_repository.get_chat_session(session_id)

        full_conversation = json.loads(chat_session.full_conversation)
        sliding_window = json.loads(chat_session.sliding_window)

        full_conversation.append(new_message)
        sliding_window.append(new_message)

        # 슬라이딩 윈도우 크기 제한
        
        
    # 채팅 세션 종료하기
    async def end_chat_session(self, session_id: int):
        logger.info(f"ChatService에서 채팅 세션 종료를 시도합니다. (session_id: {session_id})")
        async with self.db.begin():
            try:
                return await self.chat_repository.update_session(session_id)
            except Exception as e:
                logger.error(f"Error in end_chat_session: {str(e)}", exc_info=True)
                raise
