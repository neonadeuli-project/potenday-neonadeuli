import random
from app.core.config import settings

class ClovaService:
    def __init__(self):
        self.response = [
            "네 그렇군요. 더 자세히 말씀해 주시겠어요?",
            "그걸로 포텐데이 원픽 하실수 있으시겠어요?",
            "이렇게 개발하다 배포는 언제하실거에요?",
            "너나들이 개발 언제 끝나요? 광고 붙이고싶어요"
        ]
        # self.api_key = settings.CLOVA_API_KEY
        # self.api_url = settings.CLOVA_API_URL

    async def get_clova(self, session_id: int, message: str) -> str:
        # 여기서 클로바 챗봇 응답 데이터 추출
        # 임시로 
        return random.choice(self.response)