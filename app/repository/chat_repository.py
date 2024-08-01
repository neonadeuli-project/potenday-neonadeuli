import logging
from typing import List, Optional
from datetime import datetime

from fastapi import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, values, desc
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import func
from sqlalchemy.orm import joinedload

from app.models.chat.chat_session import ChatSession
from app.models.chat.chat_message import ChatMessage
from app.models.enums import RoleType
from app.models.user import User
from app.models.heritage.heritage import Heritage
from app.schemas.chat import VisitedBuilding

logger = logging.getLogger(__name__)


class ChatRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    # 채팅 세션 생성
    async def create_chat_session(self, user_id: int, heritage_id: int) -> ChatSession:
        logger.info(f"ChatRepository에서 채팅 세션을 생성합니다. (user_id: {user_id}, heritage_id: {heritage_id})")
        try:
            # 채팅 세션 활성화 상태 확인
            active_session = await self.get_active_session(user_id, heritage_id)
            if active_session:
                logger.info(f"기존 활성 세션을 반환합니다. (session_id: {active_session.id})")
                return active_session

            # 사용자 여부 확인 & 새 세션 생성
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
            logger.error(f"create_or_get_chat_session 메소드 에러 발생 : {str(e)}", exc_info=True)
            raise

    # 채팅 세션 활성화 상태 조회
    async def get_active_session(self, user_id: int, heritage_id: int) -> Optional[ChatSession]:
        result = await self.db.execute(select(ChatSession)
                                       .where(
                                           (ChatSession.user_id == user_id) &
                                           (ChatSession.heritage_id == heritage_id) &
                                           (ChatSession.end_time == None) # 세션 종료 유무 확인
                                       )
                                       .order_by(ChatSession.created_at.desc())
                                    )
        return result.scalar_one_or_none()
    
    # 채팅 세션 종료
    async def end_chat_session(self, session_id: int) -> Optional[ChatSession]:
        try:
            await self.db.execute(update(ChatSession)
                                            .where(
                                                (ChatSession.id == session_id) &
                                                (ChatSession.end_time == None)
                                            )
                                            .values(end_time=func.now())
                                        )
            await self.db.commit()

            # 업데이트 된 세션 조회
            result = await self.db.execute(select(ChatSession)
                                           .where(ChatSession.id == session_id)
                                        )
        
            updated_session = result.scalar_one_or_none()

            if updated_session:
                logger.info(f"채팅 세션 ID {session_id} 가 성공적으로 종료되었습니다.")
                # 세션 객체 반환을 위해 필요한 관계들을 로드
                # await self.db.refresh(updated_session, ['users', 'heritages', 'chat_messages'])
                return updated_session
            else:
                logger.info(f"종료할 채팅 세션 ID가 {session_id} 인 활성 세션을 찾을 수 없습니다.")
                return None
            
        except SQLAlchemyError as e:
            logger.error(f"채팅 세션 ID가 {session_id} 인 채팅 세션이 종료되는 동안 데이터 베이스에 오류가 발생했습니다.: {str(e)}")
            await self.db.rollback()
            raise ValueError(f"데이터베이스 오류 : {str(e)}")
        except Exception as e:
            logger.error(f"채팅 세션 ID가 {session_id} 인 채팅 세션이 종료되는 동안 예상치 못한 에러 발생 : {str(e)}")
            await self.db.rollback()
            raise ValueError(f"예상치 못한 오류 : {str(e)}")
    
    # 새로운 채팅 메시지 저장 (새 레코드 추가)
    async def create_message(self, session_id: int, role: RoleType, content: str) -> ChatMessage:
        # 세션 유효성 검사
        # session = await self.db.execute(select(ChatSession)
        #                                 .where(ChatSession.id == session_id))
        # session = session.scalar_one_or_none()
        # if not session:
        #     raise ValueError("채팅 세션을 찾을 수 없습니다.")
        
        new_message = ChatMessage(
            session_id=session_id,
            role=role.value,
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
    async def get_latest_message(self, session_id: int, role: RoleType) -> ChatMessage:
        query = select(ChatMessage).where(
            (ChatMessage.session_id == session_id) & 
            (ChatMessage.role == role.value)
        ).order_by(desc(ChatMessage.timestamp)).limit(1)
        result = await self.db.execute(query)
        return result.scalars().first()
    
    # 특정 채팅 세션 조회
    async def get_chat_session(self, session_id: int) -> ChatSession:
        result = await self.db.execute(select(ChatSession)
                                       .where(ChatSession.id == session_id))
        return result.scalar_one_or_none()
    
    # 채팅 요약 정보 조회
    async def get_chat_summary(self, session_id: int):
        result = await self.db.execute(select(ChatSession)
                                       .options(joinedload(ChatSession.heritages))
                                       .where(ChatSession.id == session_id)
                                    )
        chat_session = result.scalar_one_or_none()

        if chat_session and chat_session.summary_keywords and chat_session.visited_buildings:
            return {
                "chat_date": chat_session.start_time,
                "heritage_name": chat_session.heritages.name,
                "building_course": chat_session.visited_buildings,
                "keywords": chat_session.summary_keywords
            }
        
        return None
    
    # 채팅 요약 정보 저장
    async def save_chat_summary(self, session_id: int, keywords: List[str], visited_buildings: List[VisitedBuilding]):
        await self.db.execute(update(ChatSession)
                              .where(ChatSession.id == session_id)
                              .values(
                                  summary_keywords=keywords,
                                  visited_buildings=[building.model_dump() for building in visited_buildings],
                                  summary_generated_at=func.now()
                                )
                            )
        await self.db.commit()
        
    
