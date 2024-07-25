from pydantic import BaseModel

class UserTempLoginResponse(BaseModel):
    nickname: str
    access_token: str
    token_type: str
    expires_in: int