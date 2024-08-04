import asyncio
import json
import logging

from typing import Any, Callable, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.error.chat_exception import ChatServiceException, NoQuizAvailableException, QuizGenerationException
from app.error.heritage_exceptions import (
    BuildingNotFoundException, 
    InvalidAssociationException
)
from app.error.chat_exception import SessionNotFoundException
from app.models.enums import ChatbotType, RoleType
from app.service.clova_service import ClovaService
from app.service.validation_service import ValidationService
from app.repository.heritage_repository import HeritageRepository
from app.repository.chat_repository import ChatRepository
from app.repository.user_repository import UserRepository
from app.schemas.chat import (
    ChatSessionResponse, 
    ChatMessageResponse, 
    ChatSessionEndResponse, 
    VisitedBuilding
)

from app.utils.common import parse_quiz_content

logger = logging.getLogger(__name__)

class ChatService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repository = UserRepository(db)
        self.chat_repository = ChatRepository(db)
        self.heritage_repository = HeritageRepository(db)
        self.validation_service = ValidationService(db)
        self.clova_service = ClovaService()
        self.current_sliding_window = None
    
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
                logger.error(f"채팅 세션 생성 중 오류 발생: {str(e)}", exc_info=True)
                raise ChatServiceException("채팅 세션 생성 실패")
    
    # 채팅 세션 종료하기
    async def end_chat_session(self, session_id: int) -> ChatSessionEndResponse:
        logger.info(f"ChatService에서 채팅 세션 종료를 시도합니다. (session_id: {session_id})")
        try:
            ended_session = await self.chat_repository.end_chat_session(session_id)

            # 세션을 찾지 못했거나 이미 종료된 경우
            if ended_session is None:
                raise SessionNotFoundException(session_id)

            return ChatSessionEndResponse (
                session_id=ended_session.id,
                end_time=ended_session.end_time
            )
                
        except SessionNotFoundException:
            raise
        except Exception as e:
            logger.error(f"채팅 세션 종료 중 오류 발생: {str(e)}", exc_info=True)
            raise ChatServiceException("채팅 세션 종료 실패")
         
    # 채팅 핵심 로직
    async def update_conversation(self, session_id: int, content: str, clova_method: Callable):
        try:
            chat_session = await self.chat_repository.get_chat_session(session_id)
            if not chat_session:
                raise SessionNotFoundException(session_id)
            
            # 기존 대화 내용 가져오기
            full_conversation = json.loads(chat_session.full_conversation) if chat_session.full_conversation else []
            self.current_sliding_window = json.loads(chat_session.sliding_window) if chat_session.sliding_window else []

            logger.debug(f"현재 슬라이딩 윈도우: {self.current_sliding_window}")
            
            # User 메시지 저장
            await self.update_conversation_content(session_id, RoleType.USER, content, full_conversation, self.current_sliding_window)
            
            # Clova API 호출
            clova_responses = await self.get_clova_response(clova_method, session_id, self.current_sliding_window)

            bot_response = clova_responses.get("response", clova_responses)
            new_sliding_window = clova_responses.get("new_sliding_window", self.current_sliding_window)

            # Clova 메시지 저장
            await self.update_conversation_content(session_id, RoleType.ASSISTANT, bot_response, full_conversation, new_sliding_window)

            # 업데이트 된 대화 내용 저장
            await self.save_conversation(session_id, full_conversation, new_sliding_window)

            return bot_response
        except SessionNotFoundException:
            raise
        except Exception as e:
            logger.error(f"챗봇 대화 업데이트 중 오류 발생: {str(e)}", exc_info=True)
            raise ChatServiceException("대화 업데이트 실패")
    
    # 대화 내용 업데이트
    async def update_conversation_content(self, session_id: int, role: RoleType, content: str, full_conversation: list, sliding_window: list):
        content_str = json.dumps(content, ensure_ascii=False) if isinstance(content, dict) else content

        try:
            message = await self.chat_repository.create_message(session_id, role, content_str)
            full_conversation.append({"role": role.value, "content": content_str})
            if sliding_window is not None:
                sliding_window.append({"role": role.value, "content": content_str})

            return message
        except Exception as e:
            logger.error(f"대화 내용 업데이트 중 오류 발생: {str(e)}", exc_info=True)
            raise ChatServiceException("대화 내용 업데이트 실패")
    
    # Clova 응답 조회
    async def get_clova_response(self, clova_method: Callable, session_id: int, sliding_window: list, *args, **kwargs) -> dict:
        try:
            logger.info(f"메서드를 사용하여 {session_id}번 세션에 대한 Clova 응답 얻기: {clova_method.__name__}")
            logger.info(f"Sliding window 내용: {sliding_window}")

            if asyncio.iscoroutinefunction(clova_method):
                response = await clova_method(session_id, sliding_window)
            else:
                response = clova_method(session_id, sliding_window)

            if isinstance(response, str):
                return {"response": response, "new_sliding_window": sliding_window}
            return response
        except Exception as e:
            logger.error(f"Clova 응답 조회 중 오류 발생: {str(e)}", exc_info=True)
            raise ChatServiceException("Clova 응답 조회 실패")
    
    
    # 업데이트 된 대화 내용 저장
    async def save_conversation(self, session_id: int, full_conversation: list, sliding_window: list):
        try:
            await self.chat_repository.update_message(
                session_id,
                full_conversation=json.dumps(full_conversation, ensure_ascii=False),
                sliding_window=json.dumps(sliding_window, ensure_ascii=False)
            )
        except Exception as e:
            logger.error(f"대화 내용 저장 중 오류 발생: {str(e)}", exc_info=True)
            raise ChatServiceException("대화 내용 저장 실패")

    # 채팅 메시지 제공
    async def update_chat_conversation(self, session_id: int, content: str) -> ChatMessageResponse:
        try:
            # 사용자 메시지 저장 및 Clova 응답 받기
            bot_response =  await self.update_conversation(session_id, content, self.clova_service.get_chatting)

            # 가장 최근 챗봇 메시지 조회 
            # 최근 메시지 뿐 아니라 연관된 다른 컬럼 데이터도 가져올 수 있기 때문에 bot_response와 구분
            bot_message = await self.chat_repository.get_latest_message(session_id, RoleType.ASSISTANT)
            
            if bot_message is None:
                raise ChatServiceException("대화 업데이트 이후 챗봇 메시지를 찾을 수 없습니다.")

            return ChatMessageResponse (
                id=bot_message.id,
                session_id=session_id,
                role=RoleType.ASSISTANT.value,
                content=bot_response,
                timestamp=bot_message.timestamp
            )
        except Exception as e:
            logger.error(f"채팅 대화 업데이트 중 오류 발생: {str(e)}", exc_info=True)
            raise ChatServiceException("채팅 대화 업데이트 실패")

    # 문화재 건축물 정보 제공 
    async def update_info_conversation(self, session_id: int, building_id: int):
        try:
            # 세션 및 유효성 검사
            await self.validation_service.validate_session_and_building(session_id, building_id) 

            # 해당 건축물의 이미지 1개 조회
            image_urls = await self.heritage_repository.get_heritage_building_images(building_id) 
            image_url = image_urls[0].image_url if image_urls else None

            # 해당 건축물의 이름 조회
            building_name = await self.heritage_repository.get_heritage_building_name_by_id(building_id)
            if not building_name:
                raise BuildingNotFoundException(f"건축물 ID {building_id}에 해당하는 건축물 이름을 찾을 수 없습니다.")

            bot_response = await self.clova_service.get_info_or_quiz(session_id, building_name, ChatbotType.INFO)
            
            if bot_response is None:
                raise ChatServiceException("대화 업데이트 이후 건축물 정보 메시지를 찾을 수 없습니다.")

            return image_url, bot_response
        except (SessionNotFoundException, BuildingNotFoundException, InvalidAssociationException):
            raise
        except Exception as e:
            logger.error(f"건축물 정보 제공 중 오류 발생: {str(e)}", exc_info=True)
            raise ChatServiceException("건축물 정보 제공 실패")

    
    # 퀴즈 재응답 요청
    async def get_quiz_with_retry(self, session_id: int, building_name: str) -> Dict[str, Any]:
        for attempt in range(settings.MAX_RETRIES):
            try:
                quiz_response = await self.clova_service.get_info_or_quiz(session_id, building_name, ChatbotType.QUIZ)
                parsed_quiz = parse_quiz_content(quiz_response)

                if self.validation_service.is_valid_quiz(parsed_quiz):
                    return parsed_quiz
                
                logger.warning(f"{attempt + 1} 번 시도에서 잘못된 퀴즈가 생성되었습니다. 시도 중...")
            except Exception as e:
                logger.error(f"{attempt + 1} 번째 시도에 생성된 퀴즈에서 발생한 에러: {str(e)}")

            if attempt < settings.MAX_RETRIES - 1:
                await asyncio.sleep(settings.RETRY_DELAY)

        raise QuizGenerationException("유효한 퀴즈 생성 실패")
    
    # 문화재 건축물 퀴즈 제공 
    async def update_quiz_conversation(self, session_id: int, building_id: int) -> Dict[str, Any]:
        try:
            chat_session, building = await self.validation_service.validate_session_and_building(session_id, building_id)

            if chat_session.quiz_count <= 0:
                raise NoQuizAvailableException("퀴즈를 더이상 사용하실 수 없습니다.")

            # 해당 건축물의 이름 조회
            building_name = await self.heritage_repository.get_heritage_building_name_by_id(building_id)
            if not building_name:
                raise BuildingNotFoundException(f"건축물 ID {building_id} 에 해당하는 건축물 이름을 찾을 수 없습니다.")
            
            # 퀴즈 데이터 파싱
            parsed_quiz = await self.get_quiz_with_retry(session_id, building_name)

            # 퀴즈 카운트
            chat_session.quiz_count -= 1
            self.db.add(chat_session)
            await self.db.commit()

            # 퀴즈 데이터 저장
            saved_quiz = await self.heritage_repository.save_quiz_data(session_id, parsed_quiz)

            # full_conversation 퀴즈 참조 추가
            # quiz_reference = {'question': saved_quiz.question, 'options': saved_quiz.options, 'answer': saved_quiz.answer, 'explanation': saved_quiz.explanation}

            # async def quiz_reference_method(s, w):
            #     return quiz_reference

            # await self.update_conversation(session_id, building_name, quiz_reference_method)

            return {
                'question': saved_quiz.question,
                'options': json.loads(saved_quiz.options) if isinstance(saved_quiz.options, str) else saved_quiz.options,
                'answer': saved_quiz.answer,
                'explanation': saved_quiz.explanation,
                'quiz_count': chat_session.quiz_count
            }
        except (SessionNotFoundException, BuildingNotFoundException, InvalidAssociationException):
            raise
        except Exception as e:
            logger.error(f"퀴즈 대화 업데이트 중 오류 발생: {str(e)}", exc_info=True)
            raise ChatServiceException("퀴즈 대화 업데이트 실패")


    # 채팅 요약 메서드
    async def update_summary_conversation(self, session_id: int):
        try:
            chat_session = await self.chat_repository.get_chat_session(session_id)
            if not chat_session:
                raise ValueError("채팅 세션을 찾을 수 없습니다.")
            
            summary = await self.chat_repository.get_chat_summary(session_id)
            if summary:
                # building_course 문자열 리스트로 변환
                building_course = [building['name'] for building in summary['building_course'] if building['visited']]
                return {
                    'chat_date': summary['chat_date'],
                    'heritage_name': summary['heritage_name'],
                    'building_course': building_course,
                    'keywords': summary['keywords']
                }
            
            return None
        except SessionNotFoundException:
            raise
        except Exception as e:
            logger.error(f"채팅 요약 업데이트 중 오류 발생: {str(e)}", exc_info=True)
            raise ChatServiceException("채팅 요약 업데이트 실패")
    
    # 백그라운드 요약 작업
    async def generated_and_save_chat_summary(self, session_id: int, visited_buildings: List[VisitedBuilding]):
        try:
            # 방문한 건물 이름 리스트 생성
            visited_building_names = [building.name for building in visited_buildings if building.visited]

            # 방문 코스 문자열 변환
            visited_course = "->".join(visited_building_names)

            # Clova 서비스로 키워드 생성
            summary_response = await self.clova_service.get_summary(session_id, visited_course)

            # 생성된 키워드 DB 저장
            await self.chat_repository.save_chat_summary(
                session_id, 
                summary_response["keywords"],
                visited_buildings
            )
            
        except ValueError as e:
            # Clova 서비스에서 발생한 예외 처리
            logger.error(f"Clova 서비스 에러: {str(e)}")
            raise ChatServiceException("채팅 요약 생성 실패")
        except Exception as e:
            logger.error(f"채팅 요약 생성 및 저장 도중 예상치 못한 에러 발생: {str(e)}")
            raise ChatServiceException("채팅 요약 실패 및 저장 실패")