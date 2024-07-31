from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.schemas.heritage import HeritageRouteInfo, HeritageBuildingInfo

# 새로운 채팅 세션 생성 요청 값
class ChatSessionRequest(BaseModel):
    user_id: int
    heritage_id: int

# 새로운 채팅 세션 생성 응답 값
class ChatSessionResponse(BaseModel):
    session_id: int
    start_time: datetime
    created_at: datetime
    heritage_id: int
    heritage_name: str
    routes: List[HeritageRouteInfo]

# 채팅 메시지 생성 요청 값
class ChatMessageRequest(BaseModel):
    content: str
    role: str
    timestamp: datetime

# 채팅 메시지 응답 값
class ChatMessageResponse(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    timestamp: datetime
    
# 채팅 세션 종료 응답 값
class ChatSessionEndResponse(BaseModel):
    id: int
    user_id: int
    heritage_id: int
    start_time: datetime
    end_time: Optional[datetime] = None 
    created_at: datetime
    updated_at: datetime