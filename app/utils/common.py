import re
import logging
from typing import Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from korean_name_generator import namer
   
from app.error.heritage_exceptions import (
    BuildingNotFoundException, 
    InvalidAssociationException, 
    SessionNotFoundException
)
from app.models.user import User

logger = logging.getLogger(__name__)

# 생성 가능한 이름이 한정되어 있으므로 개발 초기에만 사용
def generate_random_korean_name(length=8):
    name_generator = namer.generate(True)
    return name_generator

async def get_unique_nickname(db: AsyncSession):
    while True:
        nickname = generate_random_korean_name()
        result = await db.execute(select(User).where(User.name == nickname))
        # Check if the nickname already exists in the database
        if not result.scalars().first():
            return nickname

# 퀴즈 응답 추출
def parse_quiz_content(quiz_content: str) -> Dict[str, any]:
    try:
        # 줄 바꿈 기준으로 텍스트 나눔
        lines = quiz_content.strip().split('\n')

        # 퀴즈 문제 추출
        question = lines[0].strip()
        logger.info(f"추출된 문제: {question}")

        # 선택지 추출
        options = []
        for line in lines[1:]:
            # 예시) "1. 근정전" -> "근정전" 추출
            match = re.match(r'^\d+\.\s*(.+)$', line.strip())
            if match:
                options.append(match.group(1))
            if len(options) == 5:
                break
                
        logger.info(f"추출된 선택지: {options}")

        if len(options) < 2:
            raise ValueError("최소 2개 이상의 선택지가 필요합니다.")
        
        # 정답 추출
        answer_match = re.search(r'정답:\s*(\d+)번', quiz_content)
        if answer_match:
            answer = answer_match.group(1)
            if int(answer) > len(options):
                raise ValueError(f"정답 번호({answer})가 선택지 개수({len(options)})를 초과합니다.")
            logger.info(f"추출된 정답 값 : {answer}")
        else:
            logger.warning("정답 값을 추출할 수 없습니다.")

        # 설명 추출
        explanation_match = re.search(r'설명:\s*(.+)$', quiz_content, re.DOTALL)
        if explanation_match:
            explanation = explanation_match.group(1).strip()
            logger.info(f"추출된 설명: {explanation}")
        else:
            logger.warning("설명을 찾을 수 없습니다.")

        parsed_quiz = {
            'question': question,
            'options': options,
            'answer': answer, 
            'explanation': explanation
        }
        
        # 최종 유효성 검사
        if not all([parsed_quiz['question'], parsed_quiz['options'], parsed_quiz['answer'], parsed_quiz['explanation']]):
            raise ValueError("퀴즈의 필수 요소가 누락되었습니다.")
        
        logger.info(f"성공적으로 파싱된 퀴즈: {parsed_quiz}")

        return parsed_quiz
        
    except Exception as e:
        logger.error(f"퀴즈 내용 파싱 중 오류 발생: {str(e)}")
        raise ValueError("퀴즈 내용을 파싱할 수 없습니다.") from e