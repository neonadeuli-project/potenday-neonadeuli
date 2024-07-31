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

# 정보 버튼에 제공될 내부 건축물 정보 
class HeritageBuildingInfoResponse(BaseModel):
    image_url: str
    bot_response: str

# 퀴즈 버튼에 제공될 퀴즈 정보
class QuizOption(BaseModel):
    id: int
    text: str

# 퀴즈 버튼에 제공될 퀴즈 정답 정보
class HeritageBuildingQuizResponse(BaseModel):
    quiz_text: str
    options: str
    # correct_option: int