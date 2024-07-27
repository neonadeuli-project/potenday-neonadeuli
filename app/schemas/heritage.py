from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class HeritageBuildingInfoResponse(BaseModel):
    image_url: str
    bot_response: str
