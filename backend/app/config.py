from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path

# Resolve .env relative to this file: backend/app/config.py -> ../.env
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    APP_NAME: str = "LogMorph AI"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"  # development, staging, production
    DEBUG: bool = False

    # Server
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    CORS_ORIGINS: str = "*"

    # SSL (optional — set both key + cert paths to enable HTTPS)
    SSL_KEY_FILE: str = ""
    SSL_CERT_FILE: str = ""

    # Database
    DATABASE_URL: str = "sqlite:///./logmorph.db"

    # Security / JWT
    SECRET_KEY: str = "logmorph-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 1 day
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # AI Providers
    OPENAI_API_KEY: str = ""
    AZURE_OPENAI_KEY: str = ""
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_API_VERSION: str = "2024-02-15-preview"
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
        env_file = str(ENV_FILE)
        env_file_encoding = "utf-8"
        case_sensitive = True

    @property
    def is_docs_enabled(self) -> bool:
        """Swagger/ReDoc docs are only enabled in non-production environments."""
        return self.ENVIRONMENT.lower() != "production"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS into a list."""
        if self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_ssl_enabled(self) -> bool:
        """SSL is enabled only if both key and cert file paths are set and exist."""
        return bool(
            self.SSL_KEY_FILE
            and self.SSL_CERT_FILE
            and Path(self.SSL_KEY_FILE).exists()
            and Path(self.SSL_CERT_FILE).exists()
        )

    @property
    def ssl_params(self) -> dict[str, str]:
        """Return uvicorn ssl_* params when SSL is enabled."""
        if self.is_ssl_enabled:
            return {
                "ssl_keyfile": self.SSL_KEY_FILE,
                "ssl_certfile": self.SSL_CERT_FILE,
            }
        return {}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
