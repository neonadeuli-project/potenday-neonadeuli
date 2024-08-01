import logging

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_token
from app.service.chat_service import ClovaService
from app.repository.heritage_repository import HeritageRepository
from app.repository.chat_repository import ChatRepository
from app.service.chat_service import ChatService
from app.schemas.heritage import (
    BuildingInfoButtonResponse,
    QuizInfoButtonResponse,
    QuizInfoButtonResponseTest
)    
from app.schemas.chat import (
    ChatSessionResponse, 
    ChatSessionRequest, 
    ChatMessageRequest,
    ChatMessageResponse, 
    ChatSessionEndResponse,
    ChatSummaryResponse,
    VisitedBuildingList
)
from app.error.heritage_exceptions import (
    BuildingNotFoundException, 
    InvalidAssociationException, 
    SessionNotFoundException
)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# def get_heritage_service(db: AsyncSession = Depends(get_db)) -> HeritageService:
#         chat_service = ChatService(db)
#         heritage_repository = HeritageRepository(db)
#         chat_repository = ChatRepository(db)
#         clova_service = ClovaService()
#         return HeritageService(chat_service, heritage_repository, chat_repository, clova_service)

# 새로운 채팅 세션 생성
@router.post("/sessions", response_model=ChatSessionResponse)
async def create_chat_session(
    chat_session: ChatSessionRequest, 
    db: AsyncSession = Depends(get_db)
):
    chat_service = ChatService(db)
    try:
        return await chat_service.create_chat_session(chat_session.user_id, chat_session.heritage_id)
    except ValueError as e:
        logger.warning(f"ValueError in create_chat_session: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except SQLAlchemyError as e:
        logger.error(f"SQLAlchemyError in create_chat_session: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="데이터베이스 오류가 발생했습니다.")
    except Exception as e:
        logger.error(f"Unexpected error in create_chat_session: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="서버 오류가 발생했습니다.")

# 채팅 메시지 전송
@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse)
async def add_chat_message(
    session_id: int, 
    message: ChatMessageRequest, 
    db: AsyncSession = Depends(get_db)
):
    chat_service = ChatService(db)
    try:
        bot_message_response : ChatMessageResponse = await chat_service.update_chat_conversation(session_id, message.content)
        return ChatMessageResponse (
            id=bot_message_response.id,
            session_id=bot_message_response.session_id,
            role=bot_message_response.role,
            content=bot_message_response.content,
            timestamp=bot_message_response.timestamp
        )
    except ValueError as e:
        logger.warning(f"메시지 전송 API Value 값 에러: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except SQLAlchemyError as e:
        logger.error(f"메시지 전송 API 데이터베이스: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="데이터베이스 오류가 발생했습니다.")
    except Exception as e:
        logger.error(f"메시지 전송 API 서버 에러: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="서버 오류가 발생했습니다.")

# 건축물 정보 조회
@router.get("/{session_id}/heritage/buildings/{building_id}/info", response_model=BuildingInfoButtonResponse)
async def get_heritage_building_info(
    session_id: int,
    building_id: int,
    content: str = Query(..., description="문화재에 대한 챗봇의 정보 조회"),
    db: AsyncSession = Depends(get_db)
):
    chat_service = ChatService(db)
    try:
        image_url, bot_response = await chat_service.update_info_conversation(session_id, building_id, content)
        return BuildingInfoButtonResponse(
            image_url=image_url or "",
            bot_response=bot_response or ""
        )
    except SessionNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BuildingNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidAssociationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"건축물 정보 제공 API 서버 에러: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="서버 오류가 발생했습니다.")

# 건축물 퀴즈 제공
@router.get("/{session_id}/heritage/buildings/{building_id}/quiz", response_model=QuizInfoButtonResponseTest)
async def get_heritage_building_quiz(
    session_id: int,
    building_id: int,
    db: AsyncSession = Depends(get_db)
):
    chat_service = ChatService(db)
    try:
        quiz_data = await chat_service.update_quiz_conversation(session_id, building_id)

        # return await QuizInfoButtonResponseTest(**quiz_data)
        return quiz_data

    except ValueError as e:
        logger.warning(f"퀴즈 정보 제공 API Value 값 에러: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except SQLAlchemyError as e:
        logger.error(f"퀴즈 정보 제공 API 데이터베이스: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="데이터베이스 오류가 발생했습니다.")
    except Exception as e:
        logger.error(f"퀴즈 정보 제공 API 서버 에러: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="서버 오류가 발생했습니다.")
    
# 채팅 요약 제공
@router.get("/sessions/{session_id}/summary", response_model=ChatSummaryResponse)
async def get_chat_summary(
    session_id: int,
    db: AsyncSession = Depends(get_db)
):
    chat_service = ChatService(db)
    try:
        summary = await chat_service.update_summary_conversation(session_id)

        if not summary:
            raise HTTPException(status_code=404, detail="요약 정보를 아직 사용할 수 없습니다.")
        
        return ChatSummaryResponse(**summary)
    except Exception as e:
        logger.error(f"채팅 요약 API 에러: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="서버 오류 발생")

# 채팅 세션 종료
@router.post("/sessions/{session_id}/end", response_model=ChatSessionEndResponse)
async def end_chat_session(
    session_id: int,
    # token: str = Depends(get_token),
    visited_buildings: VisitedBuildingList,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    # user_service = UserService(db)
    chat_service = ChatService(db)
    try:
        # 토큰으로 사용자 확인
        # user = await user_service.get_user_by_token(token)
        # if not user:
        #     raise HTTPException(status_code=401, detail="Invalid token")

        # 사용자가 해당 세션을 종료할 권한이 있는지 확인
        # if not await chat_service.user_can_end_session(user.id, session_id):
        #     raise HTTPException(status_code=403, detail="You don't have permission to end this session")

        # 세션 종료
        ended_session = await chat_service.end_chat_session(session_id)

        # 요약 작업 백그라운드 실행
        background_tasks.add_task(
            chat_service.generated_and_save_chat_summary,
            session_id,
            visited_buildings.buildings
        )

        return ended_session
    
    except ValueError as e:
        logger.warning(f"채팅 세션 종료 API Value 값 에러: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except SQLAlchemyError as e:
        logger.error(f"채팅 세션 종료 API 데이터베이스: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="데이터베이스 오류가 발생했습니다.")
    except Exception as e:
        logger.error(f"예상치 못한 채팅 세션 종료 API 서버 에러: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="서버 오류가 발생했습니다.")