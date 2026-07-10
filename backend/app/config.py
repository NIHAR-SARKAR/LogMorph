from pydantic_settings import BaseSettings
from functools import lru_cache
import os

class Settings(BaseSettings):
    APP_NAME: str = "LogMorph AI"
    VERSION: str = "1.0.0"
    DEBUG: bool = False

    DATABASE_URL: str = "sqlite:///./logmorph.db"
    SECRET_KEY: str = "logmorph-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # AI Providers
    OPENAI_API_KEY: str = ""
    AZURE_OPENAI_KEY: str = ""
    AZURE_OPENAI_ENDPOINT: str = ""
    ANTHROPIC_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    OLLAMA_HOST: str = "http://localhost:11434"
    LM_STUDIO_HOST: str = "http://localhost:1234"

    # File Processing
    MAX_UPLOAD_SIZE_MB: int = 500
    CHUNK_SIZE_BYTES: int = 8192
    MAX_LOG_LINES_PER_QUERY: int = 10000

    # Security
    BCRYPT_ROUNDS: int = 12
    SESSION_TIMEOUT_MINUTES: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    return Settings()
