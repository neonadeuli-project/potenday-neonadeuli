from pydantic import BaseModel
from datetime import datetime

class UserResponse(BaseModel):
    user_id: int
    oauth_id: int
    email: str
    name: str
    provider: str
    token: str
    created_at: datetime
    updated_at: datetime

# 임시 로그인 정보 응답 값
class UserTempLoginResponse(BaseModel):
    user_id: int
    name: str
    access_token: str
    token_type: str
    expires_in: int

