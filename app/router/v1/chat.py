import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.service.chat_service import ClovaService
from app.service.heritage_service import HeritageService
from app.repository.heritage_repository import HeritageRepository
from app.repository.chat_repository import ChatRepository
from app.service.chat_service import ChatService
from app.schemas.heritage import (
    HeritageBuildingInfoResponse
)    
from app.schemas.chat import (
    ChatSessionResponse, 
    ChatSessionRequest, 
    ChatMessageRequest,
    ChatMessageResponse, 
    ChatSessionEndResponse
)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# 새로운 채팅 세션 생성
@router.post("/sessions", response_model=ChatSessionResponse)
async def create_chat_session(
    chat_session: ChatSessionRequest, 
    db: AsyncSession = Depends(get_db)
):
    chat_service = ChatService(db)
    try:
        new_session = await chat_service.create_chat_session(
            user_id=chat_session.user_id, 
            heritage_id=chat_session.heritage_id
        )

        return ChatSessionResponse (
            id = new_session.id,
            user_id=new_session.user_id,
            heritage_id=new_session.heritage_id,
            start_time=new_session.start_time,
            created_at=new_session.created_at
        )
    except ValueError as e:
        logger.warning(f"ValueError in create_chat_session: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except SQLAlchemyError as e:
        logger.error(f"SQLAlchemyError in create_chat_session: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="데이터베이스 오류가 발생했습니다.")
    except Exception as e:
        logger.error(f"Unexpected error in create_chat_session: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="서버 오류가 발생했습니다.")

# 메시지 전송 및 챗봇 응답
# @router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse)
# async def add_chat_message(session_id: int, message: ChatMessageRequest, db: AsyncSession = Depends(get_db)):
#     chat_service = ChatService(db)
#     try:
#         user_message, bot_message = await chat_service.update_conversation(session_id, message.content)
#         return ChatMessageResponse (
#             id=bot_message.id,
#             session_id=bot_message.session_id,
#             role=bot_message.role,
#             content=bot_message.content,
#             timestamp=bot_message.timestamp
#         )
#     except ValueError as e:
#         logger.warning(f"ValueError in create_chat_session: {str(e)}")
#         raise HTTPException(status_code=400, detail=str(e))
#     except SQLAlchemyError as e:
#         logger.error(f"SQLAlchemyError in create_chat_session: {str(e)}", exc_info=True)
#         raise HTTPException(status_code=500, detail="데이터베이스 오류가 발생했습니다.")
#     except Exception as e:
#         logger.error(f"Unexpected error in create_chat_session: {str(e)}", exc_info=True)
#         raise HTTPException(status_code=500, detail="서버 오류가 발생했습니다.")

# 메시지 전송 및 챗봇 응답
@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse)
async def add_chat_message(session_id: int, message: ChatMessageRequest, db: AsyncSession = Depends(get_db)):
    chat_service = ChatService(db)
    try:
        bot_message = await chat_service.update_chat_conversation(session_id, message.content)
        return ChatMessageResponse (**bot_message)
    except ValueError as e:
        logger.warning(f"메시지 전송 API Value 값 에러: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except SQLAlchemyError as e:
        logger.error(f"메시지 전송 API 데이터베이스: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="데이터베이스 오류가 발생했습니다.")
    except Exception as e:
        logger.error(f"메시지 전송 API 서버 에러: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="서버 오류가 발생했습니다.")

# 건축물 관련 챗봇 정보 제공
@router.get("/{session_id}/heritage/buildings/{building_id}/info", response_model=HeritageBuildingInfoResponse)
async def get_heritage_building_info(
    session_id: int,
    building_id: int,
    content: str = Query(..., description="문화재에 대한 챗봇의 정보 조회"),
    db: Session = Depends(get_db)
):
    chat_service = ChatService(db)
    clova_service = ClovaService()
    heritage_repository = HeritageRepository(db)
    chat_repository = ChatRepository(db)
    service = HeritageService(chat_service, heritage_repository, chat_repository, clova_service)

    try:
        image_url, bot_response = await service.get_heritage_building_info(session_id, building_id, content)
        return HeritageBuildingInfoResponse(
            image_url=image_url or "",
            # bot_response=ChatInfoResponse(content=bot_response) if bot_response else None
            bot_response=bot_response or ""
        )
    except ValueError as e:
        logger.warning(f"건축물 정보 제공 API Value 값 에러: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except SQLAlchemyError as e:
        logger.error(f"건축물 정보 제공 API 데이터베이스: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="데이터베이스 오류가 발생했습니다.")
    except Exception as e:
        logger.error(f"건축물 정보 제공 API 서버 에러: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="서버 오류가 발생했습니다.")

# 건축물 관련 퀴즈 정보 제공
@router.get("/{session_id}/heritage/buildings/{building_id}/quiz")
async def get_heritage_building_quiz(
    session_id: int,
    building_id: int,
    content: str = Query(..., description="문화재에 대한 챗봇의 퀴즈 조회"),
    db: Session = Depends(get_db)
):
    chat_service = ChatService(db)
    clova_service = ClovaService()
    heritage_repository = HeritageRepository(db)
    chat_repository = ChatRepository(db)
    service = HeritageService(chat_service, heritage_repository, chat_repository, clova_service)

    try:
        quiz_response = await service.get_heritage_building_quiz(session_id, building_id, content)
        return quiz_response
    except ValueError as e:
        logger.warning(f"퀴즈 정보 제공 API Value 값 에러: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except SQLAlchemyError as e:
        logger.error(f"퀴즈 정보 제공 API 데이터베이스: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="데이터베이스 오류가 발생했습니다.")
    except Exception as e:
        logger.error(f"퀴즈 정보 제공 API 서버 에러: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="서버 오류가 발생했습니다.")

# 채팅 세션 종료
@router.post("/sessions/{session_id}/end", response_model=ChatSessionEndResponse)
async def end_chat_session(
    session_id: int, 
    db: AsyncSession = Depends(get_db)
):
    chat_service = ChatService(db)
    try:
        ended_session = await chat_service.end_chat_session(session_id)

        return ChatSessionEndResponse (
            id = ended_session.id,
            user_id=ended_session.user_id,
            heritage_id=ended_session.heritage_id,
            start_time=ended_session.start_time,
            end_time=ended_session.end_time,
            created_at=ended_session.created_at,
            updated_at=ended_session.updated_at
        )
    except ValueError as e:
        logger.warning(f"채팅 세션 종료 API Value 값 에러: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except SQLAlchemyError as e:
        logger.error(f"채팅 세션 종료 API 데이터베이스: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="데이터베이스 오류가 발생했습니다.")
    except Exception as e:
        logger.error(f"예상치 못한 채팅 세션 종료 API 서버 에러: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="서버 오류가 발생했습니다.")