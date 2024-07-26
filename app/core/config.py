from typing import Annotated, Any
from dotenv import load_dotenv

# load .env file
load_dotenv()

from pydantic import (
    MySQLDsn,
    computed_field,
    AnyUrl,
    BeforeValidator
)

from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict
)

from pydantic_core import MultiHostUrl

def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_empty=True, extra="ignore"
    )

    API_V1_STR: str

    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ]
    BACKEND_SESSION_SECRET_KEY : str

    PROJECT_NAME : str

    MYSQL_USER : str
    MYSQL_ROOT_PASSWORD : str
    MYSQL_PASSWORD : str
    MYSQL_SERVER : str
    MYSQL_PORT : int
    MYSQL_DB : str

    # 슬라이딩 윈도우 메시지 제한 설정
    MAX_SLIDING_WINDOW_SIZE : int

    #퀴즈 제한 설정
    QUIZ_COUNT : int

    @computed_field
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> MySQLDsn:
        return MultiHostUrl.build(
            scheme="mysql+aiomysql",
            username=self.MYSQL_USER,
            password=self.MYSQL_PASSWORD,
            host=self.MYSQL_SERVER,
            port=self.MYSQL_PORT,
            path=self.MYSQL_DB,
        )

settings = Settings()