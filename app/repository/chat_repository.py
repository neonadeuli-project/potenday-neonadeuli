import logging

from fastapi import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, values, desc
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

from app.models.chat.chat_session import ChatSession
from app.models.chat.chat_message import ChatMessage
from app.models.user import User
from app.models.heritage.heritage import Heritage

logger = logging.getLogger(__name__)


class ChatRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    # 채팅 세션 생성
    async def create_chat_session(self, user_id: int, heritage_id: int) -> ChatSession:
        logger.info(f"ChatRepository에서 채팅 세션을 생성합니다. (user_id: {user_id}, heritage_id: {heritage_id})")
        try:
            # 사용자 여부 확인
            user = await self.db.execute(select(User).where(User.id == user_id))
            user = user.scalar_one_or_none()
            if not user:
                raise ValueError(f"등록되지 않은 사용자입니다. (user_id: {user_id})")
            
            # 문화재 여부 확인
            heritage = await self.db.execute(select(Heritage).where(Heritage.id == heritage_id))
            heritage = heritage.scalar_one_or_none()
            if not heritage:
                raise ValueError(f"등록되지 않은 문화재입니다. (heritage_id: {heritage_id})")
            
            # 채팅 세션 생성
            new_session = ChatSession(
                user_id=user_id, 
                heritage_id=heritage_id,
                start_time=datetime.now(),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            self.db.add(new_session)
            await self.db.flush()
            await self.db.refresh(new_session)
            
            logger.info(f"새로운 채팅 세션이 생성되었습니다. (session_id: {new_session.id}, user_id: {user_id}, heritage_id: {heritage_id})")
            
            return new_session

        except ValueError as e:
            logger.error(str(e))
            raise

        except SQLAlchemyError as e:
            logger.error(f"데이터베이스 오류: {str(e)}")
            raise

        except Exception as e:
            logger.error(f"예상치 못한 오류: {str(e)}")
            raise
    
    # 새로운 채팅 메시지 저장 (새 레코드 추가)
    async def create_message(self, session_id: int, role: str, content: str) -> ChatMessage:
        # 세션 유효성 검사
        # session = await self.db.execute(select(ChatSession)
        #                                 .where(ChatSession.id == session_id))
        # session = session.scalar_one_or_none()
        # if not session:
        #     raise ValueError("채팅 세션을 찾을 수 없습니다.")
        
        new_message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            timestamp=datetime.now()
        )
        self.db.add(new_message)
        await self.db.flush()
        await self.db.refresh(new_message)
        return new_message
    
    # 기존 채팅 메시지 업데이트 (특정 레코드 수정)
    async def update_message(self, session_id: int, **kwargs):
        await self.db.execute(
            update(ChatSession).
            where(ChatSession.id == session_id).
            values(**kwargs)
        )
        await self.db.commit()
    
    # 채팅 최근 저장된 메시지 1개 조회
    async def get_latest_message(self, session_id: int, role: str) -> ChatMessage:
        query = select(ChatMessage).where(
            (ChatMessage.session_id == session_id) & 
            (ChatMessage.role == role)
        ).order_by(desc(ChatMessage.timestamp)).limit(1)
        result = await self.db.execute(query)
        return result.scalars().first()
    
    # 채팅 세션 종료
    async def update_session(self, session_id: int) -> ChatSession:
        try:
            session = await self.get_chat_session(session_id)
            if not session:
                raise ValueError("유효하지 않은 세션입니다.")
            
            # 채팅 세션 종료
            session.end_time = datetime.now()
            session.updated_at = datetime.now()
            logger.info(f"ChatRepository에서 채팅 세션을 종료합니다. (session_id: {session_id})")
            await self.db.flush()
            await self.db.refresh(session)
            return session
        except SQLAlchemyError as e:
            logger.error(f"데이터베이스 오류: {str(e)}")
            await self.db.rollback()
            raise
        except Exception as e:
            logger.error(f"예상치 못한 오류: {str(e)}")
            await self.db.rollback()
            raise 
    

    # 특정 채팅 세션 조회
    async def get_chat_session(self, session_id: int) -> ChatSession:
        result = await self.db.execute(select(ChatSession)
                                       .where(ChatSession.id == session_id))
        return result.scalar_one_or_none()
    
