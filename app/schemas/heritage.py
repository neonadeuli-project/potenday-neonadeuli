from typing import List, Optional, Tuple
from pydantic import BaseModel
from datetime import datetime


# 채팅 방에 제공될 내부 건축물 정보
class HeritageBuildingInfo(BaseModel):
    building_id: int
    name: str
    coordinate: Tuple[float, float] = (0, 0)

# 채팅 방에 제공될 내부 건축물 경로 정보    
class HeritageRouteInfo(BaseModel):
    route_id: int
    name: str
    buildings: List[HeritageBuildingInfo]

# 건축물 정보 버튼에 제공될 내부 건축물 정보 
class BuildingInfoButtonResponse(BaseModel):
    image_url: Optional[str] = None
    bot_response: Optional[str] = None

# 퀴즈 버튼에 제공될 퀴즈 정보
class QuizInfoButtonResponse(BaseModel):
    question: int
    options: List[str]
    answer: str
    explanation: str

# 퀴즈 버튼에 제공될 퀴즈 정보
class QuizInfoButtonResponseTest(BaseModel):
    quiz_content: str