from pydantic import BaseModel

# 임시 로그인 정보 응답 값
class UserTempLoginResponse(BaseModel):
    nickname: str
    access_token: str
    token_type: str
    expires_in: int