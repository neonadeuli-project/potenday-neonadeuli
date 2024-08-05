from enum import Enum

class RoleType(Enum):
    USER = "user"
    ASSISTANT = "assistant"

class RouteType(Enum):
    RECOMMENDED = "recommended"
    CUSTOM = "custom"

class ChatbotType(Enum):
    INFO = "info"
    QUIZ = "quiz"
    REC = "recommend_questions"

class ElementType(Enum):
    NATIONAL_TREASURE = "국보"
    TREASURE = "보물"
    HISTORIC_SITE = "사적"
    SCENIC_SITE = "명승"
    NATURAL_MONUMENT = "천연기념물"
    INTANGIBLE_CULTURAL_HERITAGE = "무형문화재"
    FOLKLORE_CULTURAL_HERITAGE = "민속문화재"
    REGISTERED_CULTURAL_HERITAGE = "등록문화재"
    CULTURAL_HERITAGE_MATERIAL = "문화재자료"
    LOCAL_CULTURAL_HERITAGE = "시도지정문화재"
    OTHER = "기타"