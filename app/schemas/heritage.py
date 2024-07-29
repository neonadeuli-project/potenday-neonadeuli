from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime


class HeritageBuildingInfo(BaseModel):
    building_id: int
    name: str
    visit_order: int
    
class HeritageRouteInfo(BaseModel):
    route_id: int
    name: str
    buildings: List[HeritageBuildingInfo]

class HeritageBuildingInfoResponse(BaseModel):
    image_url: str
    bot_response: str

class QuizOption(BaseModel):
    id: int
    text: str

class HeritageBuildingQuizResponse(BaseModel):
    quiz_text: str
    options: str
    # correct_option: int