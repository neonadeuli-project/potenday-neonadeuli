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

class HeritageTypeName(Enum):
    NATIONAL_TREASURE = "국보"
    TREASURE = "보물"
    HISTORIC_SITE = "사적"
    HISTORIC_SCENIC_SITE = "사적및명승"
    SCENIC_SITE = "명승"
    NATURAL_MONUMENT = "천연기념물"
    NATIONAL_INTANGIBLE_HERITAGE = "국가무형유산"
    NATIONAL_FOLK_CULTURAL_HERITAGE= "국가민속문화유산"
    TCH_OF_CITY_AND_PROV= "시도유형문화유산"
    CITY_AND_PROV_INTANGIBLE_HERITAGE= "시도무형유산"
    CITY_AND_PROV_MONUMENT= "시도기념물"
    URBAN_FOLK_CULTURAL_HERITAGE= "시도민속문화유산"
    PROV_REGISTERED_HERITAGE= "시도등록유산"
    CULTURAL_HERITAGE_MATERIALS= "문화유산자료"
    NATIONAL_REGISTERED_HERITAGE= "국가등록유산"
    NORTH_5_INTANGIBLE_HERITAGE= "이북5도무형유산"

class SortOrder(str, Enum):
    ASC = "오름차순"
    DESC = "내림차순"