import logging

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_token
from app.error.chat_exception import (
    ChatServiceException, 
    NoQuizAvailableException, 
    QuizGenerationException,
    SessionNotFoundException, 
    SummaryNotFoundException
)
from app.service.chat_service import ChatService
from app.schemas.heritage import (
    BuildingInfoButtonResponse,
    BuildingInfoButtonRequest,
    BuildingQuizButtonResponse,
    BuildingQuizButtonRequest
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
    InvalidAssociationException
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
        return await chat_service.create_chat_session(chat_session.user_id, chat_session.heritage_id)
    except ChatServiceException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"채팅 세션 생성 중 예상치 못한 오류 발생: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="서버에 오류가 발생했습니다.")


# 채팅 메시지 전송
@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse)
async def add_chat_message(
    session_id: int, 
    message: ChatMessageRequest, 
    db: AsyncSession = Depends(get_db)
):
    chat_service = ChatService(db)
    try:
        return await chat_service.update_chat_conversation(session_id, message.content)
       
    except SessionNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ChatServiceException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"메시지 전송 중 예상치 못한 오류 발생: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="서버 오류가 발생했습니다.")

# 건축물 정보 제공
@router.post("/{session_id}/heritage/buildings/info", response_model=BuildingInfoButtonResponse)
async def get_heritage_building_info(
    session_id: int,
    building_data: BuildingInfoButtonRequest,
    db: AsyncSession = Depends(get_db)
):
    chat_service = ChatService(db)
    try:
        image_url, bot_response = await chat_service.update_info_conversation(
            session_id, 
            building_data.building_id
        )
        
        return BuildingInfoButtonResponse(
            image_url=image_url or "",
            bot_response=bot_response or ""
        )
    except (SessionNotFoundException, BuildingNotFoundException, InvalidAssociationException) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ChatServiceException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"건축물 정보 제공 중 예상치 못한 오류 발생: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="서버 오류가 발생했습니다.")

# 건축물 퀴즈 제공
@router.post("/{session_id}/heritage/buildings/quiz", response_model=BuildingQuizButtonResponse)
async def get_heritage_building_quiz(
    session_id: int,
    building_data: BuildingQuizButtonRequest,
    db: AsyncSession = Depends(get_db)
):
    chat_service = ChatService(db)
    try:
        quiz_data = await chat_service.update_quiz_conversation(
            session_id, 
            building_data.building_id
        )

        return BuildingQuizButtonResponse(**quiz_data)

    except (SessionNotFoundException, BuildingNotFoundException, InvalidAssociationException) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except NoQuizAvailableException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except QuizGenerationException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except ChatServiceException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"퀴즈 제공 중 예상치 못한 오류 발생: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="서버 오류가 발생했습니다.")
    
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
    except SummaryNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ChatServiceException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"퀴즈 제공 중 예상치 못한 오류 발생: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="서버 오류가 발생했습니다.")

# 채팅 세션 종료
@router.post("/sessions/{session_id}/end", response_model=ChatSessionEndResponse)
async def end_chat_session(
    session_id: int,
    visited_buildings: VisitedBuildingList,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    chat_service = ChatService(db)
    try:
        # 세션 종료
        ended_session = await chat_service.end_chat_session(session_id)

        # 요약 작업 백그라운드 실행
        background_tasks.add_task(
            chat_service.generated_and_save_chat_summary,
            session_id,
            visited_buildings.buildings
        )

        return ended_session
    
    except SessionNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ChatServiceException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"퀴즈 제공 중 예상치 못한 오류 발생: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="서버 오류가 발생했습니다.")