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

    DATABASE_URL : str

    MYSQL_USER : str
    MYSQL_ROOT_PASSWORD : str
    MYSQL_PASSWORD : str
    MYSQL_SERVER : str
    MYSQL_PORT : int
    MYSQL_DB : str

    # 클로바 스튜디오 API
    CLOVA_API_KEY : str
    CLOVA_API_KEY_PRIMARY_VAL : str
    CLOVA_SLIDING_API_HOST : str
    CLOVA_COMPLETION_API_HOST : str
    MAX_TOKEN : int

    # 네이버 클라우드 클로바 보이스 API
    CLOVA_VOICE_URL : str
    CLOVA_VOICE_CLIENT_ID : str
    CLOVA_VOICE_CLIENT_SECRET : str

    # 네이버 클라우드 서버 및 이미지
    NCP_ACCESS_KEY : str
    NCP_SECRET_KEY : str
    NCP_REGION : str
    NCP_ENDPOINT : str
    BUCKET_NAME : str
    CDN_DOMAIN : str

    # 슬라이딩 윈도우 메시지 제한 설정
    MAX_SLIDING_WINDOW_SIZE : int

    # 퀴즈 제한 설정
    QUIZ_COUNT : int
    MAX_RETRIES : int
    RETRY_DELAY : int

    # 로그인 보안 관리
    SECRET_KEY : str
    ALGORITHM : str
    ACCESS_TOKEN_EXPIRE_MINUTES : int

    # 기본 이미지 URL
    DEFAULT_IMAGE_URL : str

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