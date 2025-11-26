from pydantic import Field, MySQLDsn  
from pydantic_settings import BaseSettings  
from typing import List, Optional

class Settings(BaseSettings):
    # ---------- MySQL ----------
    DB_HOST: str
    DB_PORT: int = 3306
    DB_USER: str
    DB_PASSWORD: str
    DB_DATABASE: str
    
    #跨域
    CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def DATABASE_URI(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_DATABASE}?charset=utf8mb4"
        )
    
    def CORS_ORIGINS_LIST(self) -> List[str]:
        """把逗号分隔的字符串拆成列表，供 FastAPI 的 allow_origins 使用"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    # ---------- JWT ----------
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()