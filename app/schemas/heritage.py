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

# 건축물 정보 버튼에 제공될 내부 건축물 정보 요청 값
class BuildingInfoButtonRequest(BaseModel): 
    building_id: int

# 건축물 정보 버튼에 제공될 내부 건축물 정보 응답 값
class BuildingInfoButtonResponse(BaseModel):
    image_url: Optional[str] = None
    bot_response: Optional[str] = None

# 퀴즈 버튼에 제공될 퀴즈 정보 요청 값
class BuildingQuizButtonRequest(BaseModel):
    building_id: int

# 퀴즈 버튼에 제공될 퀴즈 정보 응답 값
class BuildingQuizButtonResponse(BaseModel):
    question: str
    options: List[str]
    answer: int
    explanation: str
    quiz_count : int